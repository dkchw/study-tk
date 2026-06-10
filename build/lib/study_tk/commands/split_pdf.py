"""PDF Split command implementation"""

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


class SplitPDFCommand(BaseCommand, BaseTool):
    """PDF splitting command"""

    def __init__(self):
        BaseTool.__init__(self)

    def execute(self, args):
        """Execute PDF split command"""
        if not FITZ_AVAILABLE:
            print("Error: PyMuPDF library not installed. Run: pip install PyMuPDF")
            return

        pdf_files = []
        for pattern in args.files:
            pdf_files.extend(glob.glob(pattern))

        if not pdf_files:
            print("No PDF files found matching the pattern(s)")
            return

        self.split_pdfs(pdf_files, args.output, args.level, args.use_bookmark_names)

    def add_arguments(self, parser):
        """Add split-specific arguments"""
        parser.add_argument('files', nargs='+', help='PDF files to split')
        parser.add_argument('--output', '-o', default='split',
                           help='Output directory (default: split)')
        parser.add_argument('--level', '-l', type=int, default=None,
                           help='Bookmark level to split at (only for auto-split mode)')
        parser.add_argument('--use-bookmark-names', action='store_true',
                           help='Use bookmark titles as filenames when splitting')

    def split_pdfs(self, pdf_files: List[str], output_dir: str = "split",
                   bookmark_level: Optional[int] = None, use_bookmark_names: bool = False):
        """Split PDFs into multiple files"""
        os.makedirs(output_dir, exist_ok=True)

        for pdf_file in pdf_files:
            self._split_single_pdf(pdf_file, output_dir, bookmark_level, use_bookmark_names)

    def _split_single_pdf(self, filename: str, output_dir: str,
                         bookmark_level: Optional[int] = None, use_bookmark_names: bool = False):
        """Split a single PDF file"""
        doc = fitz.open(filename)
        total_pages = len(doc)

        if total_pages < 1:
            print(f"{filename} has no pages to split")
            return

        print(f"\nProcessing '{filename}' with {total_pages} pages")

        # Check for bookmarks
        all_bookmarks = self._get_all_bookmarks(doc)

        if all_bookmarks:
            # Show bookmark hierarchy
            print("\nBookmark structure:")
            bookmark_levels = {}
            for level, title, page in all_bookmarks:
                if level not in bookmark_levels:
                    bookmark_levels[level] = []
                bookmark_levels[level].append((title, page))
                indent = "  " * (level - 1)
                print(f"  {indent}[Level {level}] '{title}' - Page {page}")

            print(f"\nAvailable bookmark levels: {sorted(bookmark_levels.keys())}")

        print("\nSelect split mode:")
        print("1: Enter LAST page of each part (e.g., '5' means pages 1-5)")
        print("2: Enter FIRST page of next part (e.g., '6' means current part ends at page 5)")
        if all_bookmarks:
            print("3: Auto-split using bookmarks")

        while True:
            mode = input("Choose mode (1, 2" + (", or 3): " if all_bookmarks else "): ")).strip()
            if mode in ['1', '2']:
                break
            if mode == '3' and all_bookmarks:
                break
            print("Invalid choice! Please enter " + ("1, 2, or 3." if all_bookmarks else "1 or 2."))

        chunks = []

        if mode == '3':
            # Ask for bookmark level if not provided
            if bookmark_level is None:
                levels = sorted(set(level for level, _, _ in all_bookmarks))
                print(f"\nAvailable levels: {levels}")
                while True:
                    try:
                        level_input = input(f"Select bookmark level to split at (default: 1): ").strip()
                        if not level_input:
                            bookmark_level = 1
                            break
                        bookmark_level = int(level_input)
                        if bookmark_level in levels:
                            break
                        print(f"Invalid level! Please choose from: {levels}")
                    except ValueError:
                        print("Invalid input! Please enter a number.")

            # Filter bookmarks by selected level
            filtered_bookmarks = [(title, page) for level, title, page in all_bookmarks
                                 if level == bookmark_level]

            chunks = self._split_by_bookmarks(filtered_bookmarks, total_pages, bookmark_level)
            if chunks is None:
                return
        else:
            chunks = self._split_manually(mode, total_pages)

        if not chunks:
            print("No splits created. Skipping this file.")
            return

        # Ask for naming preference if bookmarks exist and mode is 3
        if mode == '3' and use_bookmark_names:
            self._save_pdf_chunks_with_bookmark_names(doc, filename, chunks, output_dir, filtered_bookmarks)
        else:
            self._save_pdf_chunks(doc, filename, chunks, output_dir)

    def _get_all_bookmarks(self, doc):
        """Extract all bookmarks with their levels and page numbers from the PDF"""
        bookmarks = []
        toc = doc.get_toc()
        for item in toc:
            level, title, page = item
            bookmarks.append((level, title, page))
        return bookmarks

    def _split_by_bookmarks(self, bookmarks, total_pages, level):
        """Split PDF based on bookmarks at specified level"""
        print(f"\nBookmarks at level {level}:")
        for idx, (title, page) in enumerate(bookmarks, 1):
            print(f"  {idx}. '{title}' - Page {page}")

        confirm = input(f"\nUse these level {level} bookmarks to split? (y/n): ").lower()
        if confirm != 'y':
            print("Bookmark splitting cancelled.")
            return None

        chunks = []
        last_page = 0
        for title, page in bookmarks:
            if page > 1:
                if last_page < page - 1:
                    chunks.append((last_page, page - 2))
                    last_page = page - 1

        if last_page < total_pages:
            chunks.append((last_page, total_pages - 1))

        print("\nSplit plan:")
        for idx, (start, end) in enumerate(chunks, 1):
            print(f"  Part {idx}: pages {start+1} to {end+1}")

        return chunks

    def _split_manually(self, mode, total_pages):
        """Split PDF manually with user input"""
        if mode == '1':
            print(f"\nEnter LAST page numbers for each part (press Enter when done):")
            print(f"Example: Enter '5' then '10' then '15' to create parts with pages 1-5, 6-10, 11-15, 16-end")
        else:
            print(f"\nEnter FIRST page numbers for each new part (press Enter when done):")
            print(f"Example: Enter '6' then '11' then '16' to create parts with pages 1-5, 6-10, 11-15, 16-end")

        chunks = []
        last_page = 0
        part_num = 1

        while last_page < total_pages:
            try:
                if mode == '1':
                    user_input = input(f"Part {part_num} LAST page (current: page {last_page+1}, max: {total_pages}) or press Enter to finish: ").strip()
                else:
                    user_input = input(f"Part {part_num+1} FIRST page (current: page {last_page+1}, max: {total_pages+1}) or press Enter to finish: ").strip()

                if not user_input:
                    if last_page < total_pages:
                        chunks.append((last_page, total_pages - 1))
                    break

                page_num = int(user_input)

                if mode == '1':
                    if page_num < last_page + 1:
                        print(f"Invalid input! Must be greater than or equal to {last_page + 1}")
                        continue
                    if page_num > total_pages:
                        print(f"Invalid input! Cannot exceed {total_pages}")
                        continue
                    chunks.append((last_page, page_num - 1))
                    last_page = page_num
                else:
                    if page_num < last_page + 2:
                        print(f"Invalid input! Must be greater than or equal to {last_page + 2}")
                        continue
                    if page_num > total_pages + 1:
                        print(f"Invalid input! Cannot exceed {total_pages + 1}")
                        continue
                    chunks.append((last_page, page_num - 2))
                    last_page = page_num - 1

                part_num += 1

                if last_page >= total_pages:
                    break

            except ValueError:
                print("Invalid input! Must be a number or press Enter to finish.")

        return chunks

    def _save_pdf_chunks(self, doc, filename, chunks, output_dir):
        """Save PDF chunks to separate files"""
        base_name = os.path.splitext(filename)[0]

        for idx, (start, end) in enumerate(chunks, 1):
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=start, to_page=end)
            out_path = os.path.join(output_dir, f"{base_name}_part{idx}.pdf")
            new_doc.save(out_path)
            print(f"Saved: {out_path} (pages {start+1} to {end+1})")

    def _save_pdf_chunks_with_bookmark_names(self, doc, filename, chunks, output_dir, bookmarks):
        """Save PDF chunks with bookmark titles as filenames"""
        base_name = os.path.splitext(filename)[0]

        for idx, (start, end) in enumerate(chunks):
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=start, to_page=end)

            # Get bookmark title for this chunk
            bookmark_title = f"part_{idx+1}"
            for title, page in bookmarks:
                if start <= page - 1 <= end:
                    bookmark_title = title
                    break

            # Clean title for filename
            import re
            clean_title = re.sub(r'[^\w\s-]', '', bookmark_title).strip()
            clean_title = re.sub(r'[-\s]+', '-', clean_title)

            out_path = os.path.join(output_dir, f"{base_name}_{clean_title}.pdf")
            new_doc.save(out_path)
            print(f"Saved: {out_path} (pages {start+1} to {end+1})")
