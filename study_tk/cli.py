#!/usr/bin/env python3
"""
Study Toolkit
A unified CLI tool for PDF OCR, splitting, and markdown processing.
"""

import argparse
import glob
import os
import sys
from pathlib import Path

from study_tk.commands.ocr import OCRCommand
from study_tk.commands.split_pdf import SplitPDFCommand
from study_tk.commands.pdf2jpg import PDF2JPGCommand
from study_tk.commands.split_markdown import SplitMarkdownCommand
from study_tk.commands.collect_markdown import CollectMarkdownCommand
from study_tk.commands.setup import SetupCommand
from study_tk.commands.toc import TOCCommand
from study_tk.commands.remove_empty_lines import RemoveEmptyLinesCommand
from study_tk.utils.file_helpers import select_files_interactive


def main():
    from rich.console import Console
    from rich.panel import Panel
    import questionary
    
    console = Console()

    parser = argparse.ArgumentParser(
        description="Study Toolkit - OCR, split PDFs, and process markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
 # Interactive mode (no arguments)
 %(prog)s

 # Setup Mistral API key
 %(prog)s setup

 # OCR specific PDFs
 %(prog)s ocr document.pdf report.pdf
 %(prog)s ocr *.pdf

 # OCR with single output folder
 %(prog)s ocr *.pdf --output-mode single --output my_ocr_folder

 # Split PDFs (output to 'split' folder)
 %(prog)s split document.pdf
 %(prog)s split *.pdf --output my_splits --level 2

 # Convert PDF to JPG images
 %(prog)s pdf2jpg document.pdf
 %(prog)s pdf2jpg *.pdf --dpi 200 --quality 90

 # Split markdown files at H2 level
 %(prog)s markdown document.md --level 2
 %(prog)s markdown *.md --output my_splits --level 3

 # Extract table of contents from PDFs
 %(prog)s toc document.pdf
 %(prog)s toc *.pdf --format markdown --include-pages

 # Analyze markdown file structure
 %(prog)s toc document.md --analyze-md
 %(prog)s toc document.md --analyze-md --include-counts

 # Collect all markdown files from subdirectories
 %(prog)s collect
 %(prog)s collect --path ./notes --output collected --no-recursive
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Register all commands
    commands = {
        'setup': SetupCommand(),
        'ocr': OCRCommand(),
        'split': SplitPDFCommand(),
        'pdf2jpg': PDF2JPGCommand(),
        'markdown': SplitMarkdownCommand(),
        'collect': CollectMarkdownCommand(),
        'toc': TOCCommand(),
        'remove-empty': RemoveEmptyLinesCommand(),
    }

    # Add arguments for each command
    for name, command in commands.items():
        subparser = subparsers.add_parser(name, help=f'{name} command')
        command.add_arguments(subparser)

    # If no command specified and first arg is a file, default to ocr
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-') and sys.argv[1] not in commands:
        if glob.glob(sys.argv[1]) or sys.argv[1].endswith('.pdf'):
            # Insert 'ocr' as the first argument
            sys.argv.insert(1, 'ocr')

    args = parser.parse_args()

    # Handle command-line mode
    if args.command:
        if args.command == 'setup':
            commands['setup'].execute(args)
            return
        
        if args.command in commands:
            commands[args.command].execute(args)
        else:
            parser.print_help()
        return

    # Run interactive mode
    console.print(Panel.fit(
        "[bold blue]Study Toolkit[/bold blue]\n[dim]A unified tool for OCR, PDF splitting, and markdown processing[/dim]",
        border_style="blue"
    ))

    while True:
        choice = questionary.select(
            "Select operation:",
            choices=[
                "OCR PDFs (GLM-OCR, Mistral, Local)",
                "Convert PDF to JPG images",
                "Split PDFs",
                "Split Markdown files",
                "Collect Markdown files from subdirectories",
                "Extract Table of Contents from PDFs",
                "Analyze Markdown file structure",
                "Remove empty lines from markdown files",
                "Setup API keys",
                "Exit"
            ]
        ).ask()

        if choice == "OCR PDFs (GLM-OCR, Mistral, Local)":
            from study_tk.commands.ocr import MISTRAL_AVAILABLE, ZAI_AVAILABLE, TESSERACT_AVAILABLE, TESSERACT_BINARY_FOUND

            provider_choice = questionary.select(
                "Select OCR provider:",
                choices=[
                    questionary.Choice("Z.AI GLM-OCR (Cloud, High Quality)", value="zai"),
                    questionary.Choice("Mistral AI (Cloud, High Quality)", value="mistral"),
                    questionary.Choice("Tesseract (Local, handles image folders)", value="tesseract"),
                    questionary.Choice("PyMuPDF (Local, Fast, Text-layer extraction)", value="pymupdf"),
                ]
            ).ask()

            if provider_choice == 'mistral' and not MISTRAL_AVAILABLE:
                console.print("[red]Error: Mistral AI library not available.[/red] Run: [bold]pip install mistralai[/bold]")
                continue
            if provider_choice == 'zai' and not ZAI_AVAILABLE:
                console.print("[red]Error: Z.AI SDK not available.[/red] Run: [bold]pip install zai-sdk[/bold]")
                continue
            if provider_choice == 'tesseract':
                if not TESSERACT_AVAILABLE:
                    console.print("[red]Error: Tesseract (pytesseract/Pillow) not available.[/red] Run: [bold]pip install pytesseract Pillow[/bold]")
                    continue
                if not TESSERACT_BINARY_FOUND:
                    console.print("[red]Error: Tesseract binary not found on your system.[/red]")
                    console.print("Please install Tesseract OCR:")
                    console.print("  Linux: [bold]sudo apt install tesseract-ocr[/bold]")
                    console.print("  macOS: [bold]brew install tesseract[/bold]")
                    continue

            if provider_choice == 'tesseract':
                # Common image extensions
                img_exts = ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.bmp', '*.tiff']
                files = []
                for ext in img_exts:
                    # Case-insensitive globbing
                    files.extend(list(Path('.').glob(ext)))
                    files.extend(list(Path('.').glob(ext.upper())))
                
                # Remove duplicates (e.g. if case-insensitive filesystem) and sort
                files = sorted(list(set(files)))
                file_label = "Image file"
            else:
                file_ext = "*.pdf"
                files = sorted(list(Path('.').glob(file_ext)))
                file_label = "PDF file"

            selected = select_files_interactive(files, file_label)
            if selected:
                mode_choice = "separate"
                output_dir = 'ocr_output'
                
                if provider_choice != 'tesseract':
                    mode_choice = questionary.select(
                        "Select output mode:",
                        choices=[
                            questionary.Choice("Separate folders (each PDF gets its own folder)", value="separate"),
                            questionary.Choice("Single folder (all files in one folder)", value="single"),
                        ]
                    ).ask()

                    if mode_choice == 'single':
                        output_dir = questionary.text("Output directory:", default="ocr_output").ask()

                images_only = False
                if provider_choice in ['pymupdf', 'mistral']:
                    images_only = questionary.confirm("Extract images ONLY (no markdown text)?", default=False).ask()

                ocr_cmd = OCRCommand()
                # Simulate args
                class InteractiveArgs:
                    def __init__(self, files, output_mode, output, provider, images_only):
                        self.files = [str(f) for f in files]
                        self.output_mode = output_mode
                        self.output = output
                        self.provider = provider
                        self.images_only = images_only
                        self.table_format = None
                        self.extract_header = False
                        self.extract_footer = False
                        self.tesseract_lang = 'deu+eng'
                
                args = InteractiveArgs(selected, mode_choice, output_dir, provider_choice, images_only)
                ocr_cmd.execute(args)

        elif choice == "Convert PDF to JPG images":
            from study_tk.commands.pdf2jpg import FITZ_AVAILABLE
            if not FITZ_AVAILABLE:
                console.print("[red]Error: PyMuPDF library not installed.[/red] Run: [bold]pip install PyMuPDF[/bold]")
                continue
            
            pdf_files = sorted(list(Path('.').glob('*.pdf')))
            selected = select_files_interactive(pdf_files, "PDF file")
            if selected:
                dpi = questionary.text("DPI (Resolution):", default="150").ask()
                quality = questionary.text("JPEG Quality (1-100):", default="85").ask()
                
                pdf2jpg_cmd = PDF2JPGCommand()
                class InteractiveArgs:
                    def __init__(self, files, dpi, quality):
                        self.files = [str(f) for f in files]
                        self.output = None
                        self.dpi = int(dpi)
                        self.quality = int(quality)
                args = InteractiveArgs(selected, dpi, quality)
                pdf2jpg_cmd.execute(args)

        elif choice == "Split PDFs":
            from study_tk.commands.split_pdf import FITZ_AVAILABLE
            if not FITZ_AVAILABLE:
                console.print("[red]Error: PyMuPDF library not installed.[/red] Run: [bold]pip install PyMuPDF[/bold]")
                continue
            
            pdf_files = sorted(list(Path('.').glob('*.pdf')))
            selected = select_files_interactive(pdf_files, "PDF file")
            if selected:
                use_bookmark_names = questionary.confirm("Use bookmark names for split files?", default=False).ask()
                
                split_cmd = SplitPDFCommand()
                class InteractiveArgs:
                    def __init__(self, files, use_bookmark_names):
                        self.files = [str(f) for f in files]
                        self.output = 'split'
                        self.level = None
                        self.use_bookmark_names = use_bookmark_names
                args = InteractiveArgs(selected, use_bookmark_names)
                split_cmd.execute(args)

        elif choice == "Split Markdown files":
            md_files = sorted(list(Path('.').glob("*.md")))
            selected = select_files_interactive(md_files, "Markdown file")
            if selected:
                level = questionary.select(
                    "Split at heading level:",
                    choices=["1", "2", "3", "4", "5", "6"],
                    default="1"
                ).ask()
                
                use_heading_names = questionary.confirm("Use heading names for split files?", default=True).ask()

                md_cmd = SplitMarkdownCommand()
                class InteractiveArgs:
                    def __init__(self, files, level, use_heading_names):
                        self.files = [str(f) for f in files]
                        self.output = 'split'
                        self.level = int(level)
                        self.use_heading_names = use_heading_names
                args = InteractiveArgs(selected, level, use_heading_names)
                md_cmd.execute(args)

        elif choice == "Collect Markdown files from subdirectories":
            search_path = questionary.text("Search path:", default=".").ask()
            output_dir = questionary.text("Output directory:", default="collected_md").ask()
            recursive = questionary.confirm("Search recursively?", default=True).ask()

            collect_cmd = CollectMarkdownCommand()
            class InteractiveArgs:
                def __init__(self, path, output, no_recursive):
                    self.path = path
                    self.output = output
                    self.no_recursive = no_recursive
            args = InteractiveArgs(search_path, output_dir, not recursive)
            collect_cmd.execute(args)

        elif choice == "Extract Table of Contents from PDFs":
            from study_tk.commands.toc import FITZ_AVAILABLE
            if not FITZ_AVAILABLE:
                console.print("[red]Error: PyMuPDF library not installed.[/red] Run: [bold]pip install PyMuPDF[/bold]")
                continue
            
            pdf_files = sorted(list(Path('.').glob("*.pdf")))
            selected = select_files_interactive(pdf_files, "PDF file")
            if selected:
                output_format = questionary.select(
                    "Select output format:",
                    choices=[
                        questionary.Choice("Markdown", value="markdown"),
                        questionary.Choice("Text", value="text"),
                    ]
                ).ask()

                include_pages = questionary.confirm("Include page numbers?", default=True).ask()
                output_dir = questionary.text("Output directory:", default=".").ask()

                toc_cmd = TOCCommand()
                class InteractiveArgs:
                    def __init__(self, files, output, format, include_pages):
                        self.files = [str(f) for f in files]
                        self.output = output
                        self.format = format
                        self.include_pages = include_pages
                        self.analyze_md = False
                args = InteractiveArgs(selected, output_dir, output_format, include_pages)
                toc_cmd.execute(args)

        elif choice == "Analyze Markdown file structure":
            md_files = sorted(list(Path('.').glob("*.md")))
            selected = select_files_interactive(md_files, "Markdown file")
            if selected:
                include_counts = questionary.confirm("Include subheading/line counts?", default=True).ask()
                output_dir = questionary.text("Output directory:", default=".").ask()

                toc_cmd = TOCCommand()
                class InteractiveArgs:
                    def __init__(self, files, output, include_counts):
                        self.files = [str(f) for f in files]
                        self.output = output
                        self.analyze_md = True
                        self.include_counts = include_counts
                args = InteractiveArgs(selected, output_dir, include_counts)
                toc_cmd.execute(args)

        elif choice == "Remove empty lines from markdown files":
            md_files = sorted(list(Path('.').glob("*.md")))
            selected = select_files_interactive(md_files, "Markdown file")
            if selected:
                mode = questionary.select(
                    "Select operation mode:",
                    choices=[
                        questionary.Choice("Create new files (original file preserved)", value="new"),
                        questionary.Choice("Modify files in place", value="inplace"),
                    ]
                ).ask()

                inplace = mode == "inplace"
                output_dir = "."
                if not inplace:
                    output_dir = questionary.text("Output directory:", default="processed_md").ask()

                remove_empty_cmd = RemoveEmptyLinesCommand()
                class InteractiveArgs:
                    def __init__(self, files, inplace, output):
                        self.files = [str(f) for f in files]
                        self.inplace = inplace
                        self.output = output
                args = InteractiveArgs(selected, inplace, output_dir)
                remove_empty_cmd.execute(args)

        elif choice == "Setup API keys":
            commands['setup'].execute(None)

        elif choice == "Exit":
            console.print("[bold green]Goodbye![/bold green]")
            break


if __name__ == "__main__":
    main()
