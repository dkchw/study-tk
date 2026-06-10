"""Markdown Collect command implementation"""

import os
import shutil
from pathlib import Path
from typing import List

from study_tk.core.base_tool import BaseTool
from study_tk.commands.base_command import BaseCommand


class CollectMarkdownCommand(BaseCommand, BaseTool):
    """Markdown collection command"""

    def __init__(self):
        BaseTool.__init__(self)

    def execute(self, args):
        """Execute markdown collection command"""
        recursive = not args.no_recursive
        self.collect_markdown_files(args.path, args.output, recursive)

    def add_arguments(self, parser):
        """Add collect-specific arguments"""
        parser.add_argument('--path', '-p', default='.',
                           help='Search path (default: current directory)')
        parser.add_argument('--output', '-o', default='collected_md',
                           help='Output directory (default: collected_md)')
        parser.add_argument('--no-recursive', action='store_true',
                           help='Do not search recursively')

    def collect_markdown_files(self, search_path: str = ".", output_dir: str = "collected_md",
                              recursive: bool = True):
        """Find all markdown files in subdirectories and copy to output folder"""
        search_path = Path(search_path)
        output_path = Path(output_dir)

        # Create output directory
        output_path.mkdir(exist_ok=True)

        # Find all markdown files
        if recursive:
            md_files = list(search_path.rglob("*.md"))
        else:
            md_files = list(search_path.glob("*.md"))

        # Exclude files already in the output directory
        md_files = [f for f in md_files if not f.is_relative_to(output_path)]

        if not md_files:
            print(f"No markdown files found in '{search_path}'" +
                  (" (recursive)" if recursive else ""))
            return

        print(f"\nFound {len(md_files)} markdown file(s):")

        copied_count = 0
        skipped_count = 0

        for md_file in md_files:
            relative_path = md_file.relative_to(search_path)
            print(f"  {relative_path}")

            # Create a safe filename that preserves directory structure
            # Replace path separators with underscores
            safe_name = str(relative_path).replace(os.sep, '_')
            destination = output_path / safe_name

            # Check if file already exists
            if destination.exists():
                print(f"    → Skipped (already exists): {destination.name}")
                skipped_count += 1
                continue

            # Copy the file
            try:
                shutil.copy2(md_file, destination)
                print(f"    → Copied to: {destination.name}")
                copied_count += 1
            except Exception as e:
                print(f"    → Error copying: {str(e)}")

        print(f"\n✓ Collected {copied_count} file(s) to '{output_dir}/'")
        if skipped_count > 0:
            print(f"  Skipped {skipped_count} file(s) (already exist)")
