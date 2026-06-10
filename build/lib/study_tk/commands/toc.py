"""Table of Contents (TOC) extraction command implementation"""

import os
import glob
import re
from pathlib import Path
from typing import List

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

from study_tk.core.base_tool import BaseTool
from study_tk.commands.base_command import BaseCommand


class TOCCommand(BaseCommand, BaseTool):
    """Table of Contents extraction command"""

    def __init__(self):
        BaseTool.__init__(self)

    def execute(self, args):
        """Execute TOC extraction command"""
        # Handle markdown analysis mode
        if hasattr(args, 'analyze_md') and args.analyze_md:
            self._analyze_markdown_files(args)
            return

        if not FITZ_AVAILABLE:
            print("Error: PyMuPDF library not installed. Run: pip install PyMuPDF")
            return

        pdf_files = []
        for pattern in args.files:
            pattern_str = str(pattern)  # Convert Path objects to strings
            pdf_files.extend(glob.glob(pattern_str))

        if not pdf_files:
            print("No PDF files found matching the pattern(s)")
            return

        self.extract_toc_from_pdfs(pdf_files, args.output, args.format, args.include_pages)

    def add_arguments(self, parser):
        """Add TOC-specific arguments"""
        parser.add_argument('files', nargs='+', help='PDF files to extract TOC from or markdown files to analyze')
        parser.add_argument('--output', '-o', default='.',
                           help='Output directory (default: current directory)')
        parser.add_argument('--format', '-f', choices=['markdown', 'text'],
                           default='markdown',
                           help="Output format: 'markdown' or 'text' (default: 'markdown')")
        parser.add_argument('--include-pages', action='store_true',
                           help='Include page numbers in the output')
        parser.add_argument('--analyze-md', action='store_true',
                           help='Analyze markdown file structure instead of PDF TOC extraction')
        parser.add_argument('--include-counts', action='store_true',
                           help='Include subheading/line counts in markdown analysis (only with --analyze-md)')

    def extract_toc_from_pdfs(self, pdf_files: List[str], output_dir: str = "toc",
                              output_format: str = "markdown", include_pages: bool = False):
        """Extract table of contents from PDF files"""
        os.makedirs(output_dir, exist_ok=True)

        for pdf_file in pdf_files:
            self._extract_single_pdf_toc(pdf_file, output_dir, output_format, include_pages)

    def _extract_single_pdf_toc(self, pdf_file: str, output_dir: str,
                               output_format: str, include_pages: bool = False):
        """Extract TOC from a single PDF file"""
        try:
            doc = fitz.open(pdf_file)
            toc = doc.get_toc()

            if not toc:
                print(f"No bookmarks found in '{pdf_file}'. Skipping.")
                return

            base_name = Path(pdf_file).stem

            if output_format == 'markdown':
                output_file = os.path.join(output_dir, f"{base_name}_toc.md")
                self._write_markdown_toc(toc, output_file, include_pages)
            else:  # text format
                output_file = os.path.join(output_dir, f"{base_name}_toc.txt")
                self._write_text_toc(toc, output_file, include_pages)

            print(f"Extracted TOC from '{pdf_file}' to '{output_file}'")

        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")

    def _write_markdown_toc(self, toc, output_file: str, include_pages: bool = False):
        """Write TOC to a markdown file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for level, title, page in toc:
                # Sanitize title to remove surrogate characters
                title = title.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                if level >= 1 and level <= 6:
                    # Create heading based on level
                    header_level = '#' * level
                    if include_pages:
                        f.write(f"{header_level} {title} (Page {page})\n\n")
                    else:
                        f.write(f"{header_level} {title}\n\n")
                elif level > 6:
                    # For levels beyond 6, use dashes with indentation
                    indent = '\t' * (level - 6) if level > 6 else '\t'
                    if include_pages:
                        f.write(f"{indent}- {title} (Page {page})\n")
                    else:
                        f.write(f"{indent}- {title}\n")

    def _write_text_toc(self, toc, output_file: str, include_pages: bool = False):
        """Write TOC to a text file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for level, title, page in toc:
                # Sanitize title to remove surrogate characters
                title = title.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                indent = '  ' * (level - 1)  # Two spaces per level
                if include_pages:
                    f.write(f"{indent}{title} (Page {page})\n")
                else:
                    f.write(f"{indent}{title}\n")

    def _analyze_markdown_files(self, args):
        """Analyze markdown file structure and count subheadings"""
        md_files = []
        for pattern in args.files:
            pattern_str = str(pattern)  # Convert Path objects to strings
            if pattern_str.endswith('.md'):
                md_files.extend(glob.glob(pattern_str))
            else:
                # Try adding .md extension
                md_files.extend(glob.glob(f"{pattern_str}*.md"))

        if not md_files:
            print("No markdown files found matching the pattern(s)")
            return

        output_dir = args.output if hasattr(args, 'output') else 'toc'
        os.makedirs(output_dir, exist_ok=True)

        include_counts = args.include_counts if hasattr(args, 'include_counts') else False

        for md_file in md_files:
            self._analyze_single_markdown(md_file, output_dir, include_counts)

    def _analyze_single_markdown(self, md_file: str, output_dir: str, include_counts: bool = False):
        """Analyze structure of a single markdown file"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            result_lines = []

            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Check if line is a heading
                heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)

                if heading_match:
                    hashes = heading_match.group(1)
                    heading_text = heading_match.group(2)
                    level = len(hashes)

                    if include_counts:
                        # Count subheadings at the next level
                        subheading_count = self._count_subheadings(lines, i + 1, level)

                        # Count content lines if no subheadings
                        content_line_count = 0
                        if subheading_count == 0:
                            content_line_count = self._count_content_lines(lines, i + 1, level)

                        # Format the result line with counts
                        if subheading_count > 0:
                            result_line = f"{hashes} {heading_text} ({subheading_count})\n\n"
                        elif content_line_count > 0:
                            result_line = f"{hashes} {heading_text} ({content_line_count})\n\n"
                        else:
                            result_line = f"{hashes} {heading_text}\n\n"
                    else:
                        # Format without counts
                        result_line = f"{hashes} {heading_text}\n\n"

                    result_lines.append(result_line)

                i += 1

            # Generate output filename
            input_path = Path(md_file)
            suffix = "_analysis_counted" if include_counts else "_analysis"
            output_file = os.path.join(output_dir, f"{input_path.stem}{suffix}.md")

            # Write results
            with open(output_file, 'w', encoding='utf-8') as f:
                f.writelines(result_lines)

            count_msg = "with counts" if include_counts else "without counts"
            print(f"Analyzed '{md_file}' -> '{output_file}' ({len(result_lines)} headings, {count_msg})")

        except Exception as e:
            print(f"Error analyzing {md_file}: {str(e)}")

    def _count_subheadings(self, lines: List[str], start_idx: int, parent_level: int) -> int:
        """Count immediate subheadings of a given level"""
        count = 0
        for i in range(start_idx, len(lines)):
            match = re.match(r'^(#{1,6})\s+(.+)$', lines[i].strip())
            if match:
                level = len(match.group(1))
                if level <= parent_level:
                    break
                if level == parent_level + 1:
                    count += 1
        return count

    def _count_content_lines(self, lines: List[str], start_idx: int, parent_level: int) -> int:
        """Count non-empty content lines until next heading of same or higher level"""
        count = 0
        for i in range(start_idx, len(lines)):
            line = lines[i].strip()
            # Check if it's a heading
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                if level <= parent_level:
                    break
            else:
                # Count non-empty lines
                if line:
                    count += 1
        return count
