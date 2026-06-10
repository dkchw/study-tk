{
  description = "Study Toolkit - OCR, split PDFs, and process markdown files";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      pkgsFor = system: nixpkgs.legacyPackages.${system};
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = pkgsFor system;
          python = pkgs.python3;
          
          # Packaging zai-sdk which is not present in nixpkgs
          zai-sdk = python.pkgs.buildPythonPackage rec {
            pname = "zai-sdk";
            version = "0.2.2";
            format = "setuptools";

            src = python.pkgs.fetchPypi {
              inherit pname version;
              hash = "sha256-hBrxiFhsQfD5irytF7Fi3JdGHDq4s9Cfk7AzPr3+csM=";
            };

            propagatedBuildInputs = with python.pkgs; [
              cachetools
              httpx
              pydantic
              pyjwt
              sniffio
            ];

            doCheck = false;
          };

          study-tk = python.pkgs.buildPythonApplication {
            pname = "study-tk";
            version = "3.7.1";
            format = "pyproject";

            src = ./.;

            nativeBuildInputs = with python.pkgs; [
              setuptools
              wheel
            ];

            propagatedBuildInputs = with python.pkgs; [
              pymupdf
              pymupdf4llm
              mistralai
              zai-sdk
              rich
              questionary
              tqdm
              pytesseract
              pillow
            ];

            # Ensure tesseract binary is in PATH for pytesseract commands
            makeWrapperArgs = [
              "--prefix PATH : ${nixpkgs.lib.makeBinPath [ pkgs.tesseract ]}"
            ];

            meta = with nixpkgs.lib; {
              description = "Study Toolkit - OCR, split PDFs, and process markdown files";
              homepage = "https://github.com/dkchw/study-tk";
              license = licenses.mit;
              mainProgram = "study-tk";
            };
          };
        in
        {
          inherit study-tk;
          default = study-tk;
        });

      homeManagerModules = {
        study-tk = { config, lib, pkgs, ... }:
          let
            cfg = config.programs.study-tk;
          in
          {
            options.programs.study-tk = {
              enable = lib.mkEnableOption "Study Toolkit (study-tk)";
              package = lib.mkOption {
                type = lib.types.package;
                default = self.packages.${pkgs.system}.default;
                description = "The study-tk package to install.";
              };
            };

            config = lib.mkIf cfg.enable {
              home.packages = [ cfg.package ];
            };
          };
        default = self.homeManagerModules.study-tk;
      };

      devShells = forAllSystems (system:
        let
          pkgs = pkgsFor system;
          study-tk-pkg = self.packages.${system}.study-tk;
        in
        {
          default = pkgs.mkShell {
            inputsFrom = [ study-tk-pkg ];
            packages = with pkgs.python3Packages; [
              python-dotenv
            ];
          };
        });
    };
}
