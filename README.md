# Study Toolkit

Study Toolkit is a unified CLI tool for PDF OCR, splitting, and markdown processing.

## Features

- **Modern TUI**: Enhanced interactive interface using `rich` and `questionary`.
- **OCR PDFs**: Process PDFs using Mistral AI, Z.AI (GLM-OCR), or local extraction via `pymupdf4llm`.
- **Local OCR**: 
  - **Tesseract**: Perform OCR locally on image folders (supports JPG, PNG).
  - **PaddleOCR**: High-quality local OCR via PP-StructureV3.
  - **PyMuPDF**: Fast text-layer extraction.
- **Image Extraction**: Option to only extract images from PDFs.
- **Split PDFs**: Split PDFs based on bookmarks or page ranges.
- **Split Markdown**: Split markdown files by heading levels.
- **Collect Markdown**: Collect markdown files from subdirectories.
- **Extract TOC**: Extract table of contents from PDFs or analyze markdown structure.
- **Remove Empty Lines**: Clean up markdown files by removing excessive empty lines.

## Installation

```bash
# Core installation (includes Tesseract support)
pip install study-tk

# For PaddleOCR support:
pip install "study-tk[paddle]"

# Ensure Tesseract binary is installed on your system for Tesseract OCR:
# Linux: sudo apt install tesseract-ocr
# macOS: brew install tesseract
# Windows: Install from https://github.com/UB-Mannheim/tesseract/wiki
```

## Usage

Study Toolkit features a beautiful, interactive TUI. Just run:

```bash
study-tk
```

Or use specific commands:

```bash
# OCR with specific provider
study-tk ocr document.pdf --provider zai
study-tk ocr document.pdf --provider mistral

# Local Tesseract OCR (on images)
study-tk ocr "*.jpg" --provider tesseract

# Local PaddleOCR
study-tk ocr document.pdf --provider paddle
```