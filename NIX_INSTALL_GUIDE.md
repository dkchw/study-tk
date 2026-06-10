# Nix & Home Manager Installation Guide for Study Toolkit

This guide explains how to install and use **Study Toolkit** (`study-tk`) using **Nix Flakes** and **Home Manager**.

---

## 1. Quick Try (No Installation)

If you just want to run the tool without permanently installing it, you can run it directly:

```bash
# From the local project root
nix run .

# Or from a remote repository (if pushed)
nix run github:yourusername/study-tk
```

---

## 2. Installing via Home Manager (with Flakes)

To integrate `study-tk` into your existing Home Manager flake configuration, follow these steps:

### Step A: Add to your Flake Inputs

In your system or home-manager configuration `flake.nix`, add this repository to the `inputs` section:

```nix
{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    
    # Add study-tk input (use path: prefix for local testing, or github: format for remote)
    study-tk.url = "path:/path/to/study-tk"; 
    # Or once pushed to github:
    # study-tk.url = "github:yourusername/study-tk";
  };

  outputs = { self, nixpkgs, ... }@inputs: {
    # Your system/home configurations
  };
}
```

### Step B: Option 1 — Using the Home Manager Module (Recommended)

The flake exposes a custom Home Manager module that registers options under `programs.study-tk` and handles the installation.

1. Import the module into your Home Manager configuration (usually in `home.nix` or where your user configuration is defined):

   ```nix
   { inputs, pkgs, ... }: {
     imports = [
       inputs.study-tk.homeManagerModules.default
     ];

     # Enable the program
     programs.study-tk.enable = true;

     # (Optional) Override the package to use a custom build
     # programs.study-tk.package = inputs.study-tk.packages.${pkgs.system}.default;
   }
   ```

2. Rebuild your Home Manager generation:

   ```bash
   home-manager switch --flake .#your-username
   ```

### Step C: Option 2 — Adding directly to `home.packages`

If you do not want to use the module and just want the package:

```nix
{ inputs, pkgs, ... }: {
  home.packages = [
    inputs.study-tk.packages.${pkgs.system}.default
  ];
}
```

---

## 3. Development Shell

If you are modifying the python code or want to run tests/scripts inside the project environment with all dependencies (including `tesseract` and python libraries), you can enter the development shell:

```bash
nix develop
```

This will drop you into a shell containing:
- Python 3 with `pymupdf`, `pymupdf4llm`, `mistralai`, `zai-sdk`, `rich`, `questionary`, `tqdm`, `pytesseract`, `pillow`, and `python-dotenv`.
- The `tesseract` binary in your `PATH`.

---

## 4. Key Benefits of this Nix Packaging

- **Automatic Binary Wrapping**: The Nix package is wrapped so that `tesseract` is automatically prefixed to the `PATH` of the `study-tk` executable. You do not need to install Tesseract globally on your system.
- **Self-contained Dependencies**: It packages `zai-sdk` (which is not available in upstream nixpkgs) inline within the flake, ensuring the application builds successfully without user intervention.
