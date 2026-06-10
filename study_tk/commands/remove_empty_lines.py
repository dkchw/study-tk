"""Remove empty lines from markdown files command implementation"""

import os
import re
from pathlib import Path
from typing import List

from study_tk.commands.base_command import BaseCommand


class RemoveEmptyLinesCommand(BaseCommand):
    """Remove empty lines from markdown files command"""

    def __init__(self):
        pass

    def execute(self, args):
        """Execute remove empty lines command"""
        md_files = []
        for pattern in args.files:
            pattern_str = str(pattern)  # Convert Path objects to strings
            if pattern_str.endswith('.md'):
                md_files.extend(self._glob_safe(pattern_str))
            else:
                # Try adding .md extension
                md_files.extend(self._glob_safe(f"{pattern_str}*.md"))

        if not md_files:
            print("No markdown files found matching the pattern(s)")
            return

        for md_file in md_files:
            self._remove_empty_lines_from_file(md_file, args.inplace, args.output)

    def _glob_safe(self, pattern: str) -> List[str]:
        """Safely get files matching pattern, handling both files and directories"""
        files = []
        # First try direct file match
        if Path(pattern).is_file():
            files.append(pattern)
        else:
            # Then try glob pattern
            files.extend([str(p) for p in Path('.').glob(pattern)])
        return files

    def _remove_empty_lines_from_file(self, md_file: str, inplace: bool = False, output_dir: str = "."):
        """Remove empty lines from a single markdown file"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()

            # Remove empty lines (lines that are empty or contain only whitespace)
            filtered_lines = [line for line in original_lines if line.strip()]

            if inplace:
                # Write back to the same file
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.writelines(filtered_lines)
                print(f"Removed empty lines from '{md_file}' (modified in place)")
            else:
                # Write to output directory
                input_path = Path(md_file)
                if output_dir == ".":
                    output_file = input_path.parent / f"{input_path.stem}_no_empty_lines{input_path.suffix}"
                else:
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = Path(output_dir) / f"{input_path.stem}_no_empty_lines{input_path.suffix}"

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.writelines(filtered_lines)
                
                print(f"Removed empty lines from '{md_file}' -> '{output_file}'")

        except Exception as e:
            print(f"Error processing {md_file}: {str(e)}")

    def add_arguments(self, parser):
        """Add remove empty lines specific arguments"""
        parser.add_argument('files', nargs='+', help='Markdown files to remove empty lines from')
        parser.add_argument('--inplace', '-i', action='store_true',
                           help='Modify files in place instead of creating new files')
        parser.add_argument('--output', '-o', default='.',
                           help='Output directory (default: current directory, ignored if --inplace is used)')