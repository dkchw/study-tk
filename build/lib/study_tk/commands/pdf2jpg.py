"""PDF to JPG conversion command implementation"""

import os
import glob
from pathlib import Path
from typing import List, Optional

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

from study_tk.core.base_tool import BaseTool
from study_tk.commands.base_command import BaseCommand


class PDF2JPGCommand(BaseCommand, BaseTool):
    """PDF to JPG conversion command"""

    def __init__(self):
        BaseTool.__init__(self)

    def execute(self, args):
        """Execute PDF to JPG command"""
        if not FITZ_AVAILABLE:
            print("Error: PyMuPDF library not installed. Run: pip install PyMuPDF")
            return

        pdf_files = []
        for pattern in args.files:
            pdf_files.extend(glob.glob(pattern))

        if not pdf_files:
            print("No PDF files found matching the pattern(s)")
            return

        self.convert_pdfs(pdf_files, args.output, args.dpi, args.quality)

    def add_arguments(self, parser):
        """Add pdf2jpg-specific arguments"""
        parser.add_argument('files', nargs='+', help='PDF files to convert')
        parser.add_argument('--output', '-o', default=None,
                           help='Output directory (default: PDF_name_jpg)')
        parser.add_argument('--dpi', '-d', type=int, default=150,
                           help='Resolution for rendering (default: 150)')
        parser.add_argument('--quality', '-q', type=int, default=85,
                           help='JPEG compression quality (1-100, default: 85)')

    def convert_pdfs(self, pdf_files: List[str], output_dir: Optional[str] = None,
                    dpi: int = 150, quality: int = 85):
        """Convert multiple PDFs to JPG images"""
        for pdf_file in pdf_files:
            self._convert_single_pdf(pdf_file, output_dir, dpi, quality)

    def _convert_single_pdf(self, pdf_path: str, output_folder: Optional[str] = None,
                           dpi: int = 150, quality: int = 85):
        """
        Convert each page of a PDF to a JPG image.
        """
        if not os.path.exists(pdf_path):
            print(f"Error: PDF file not found at '{pdf_path}'")
            return

        # Open the PDF
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"Failed to open PDF {pdf_path}: {e}")
            return

        # Prepare output folder
        if output_folder is None:
            output_folder = os.path.splitext(pdf_path)[0] + "_jpg"
        
        os.makedirs(output_folder, exist_ok=True)

        # Calculate zoom factor from DPI (default PDF DPI is 72)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        total = len(doc)
        print(f"Converting {pdf_path} ({total} pages) to JPG at {dpi} DPI...")

        for page_num, page in enumerate(doc, start=1):
            # Render page to a pixmap
            pix = page.get_pixmap(matrix=mat, dpi=dpi)

            # Build output filename
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            out_file = os.path.join(output_folder, f"{base_name}_page_{page_num:03d}.jpg")

            # Save as JPEG
            pix.save(out_file, "jpeg", jpg_quality=quality)
            print(f"  ✓ Saved: {out_file}")

        doc.close()
        print(f"Done! Images saved in: {output_folder}\n")
