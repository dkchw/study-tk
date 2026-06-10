"""Markdown Split command implementation"""

import os
import glob
import re
from pathlib import Path
from typing import List

from study_tk.core.base_tool import BaseTool
from study_tk.commands.base_command import BaseCommand


class SplitMarkdownCommand(BaseCommand, BaseTool):
    """Markdown splitting command"""

    def __init__(self):
        BaseTool.__init__(self)

    def execute(self, args):
        """Execute markdown split command"""
        md_files = []
        for pattern in args.files:
            md_files.extend(glob.glob(pattern))

        if not md_files:
            print("No markdown files found matching the pattern(s)")
            return

        self.split_markdown_files(md_files, args.output, args.level, args.use_heading_names)

    def add_arguments(self, parser):
        """Add markdown-specific arguments"""
        parser.add_argument('files', nargs='+', help='Markdown files to split')
        parser.add_argument('--output', '-o', default='split',
                           help='Output directory (default: split)')
        parser.add_argument('--level', '-l', type=int, default=1,
                           help='Heading level to split at (default: 1 for H1)')
        parser.add_argument('--use-heading-names', action='store_true',
                           help='Use heading titles as filenames when splitting')

    def split_markdown_files(self, md_files: List[str], output_dir: str = "split",
                           heading_level: int = 1, use_heading_names: bool = False):
        """Split markdown files at specified heading level"""
        os.makedirs(output_dir, exist_ok=True)

        print(f"\nProcessing {len(md_files)} file(s) at heading level {heading_level}:")
        for file in md_files:
            print(f"\nProcessing: {file}")
            try:
                new_files = self._split_single_markdown(file, output_dir, heading_level, use_heading_names)
                if not new_files:
                    print(f"  → No H{heading_level} headings found. No files created.")
            except Exception as e:
                print(f"  → Error processing {file}: {str(e)}")

        print(f"\nDone! Original files remain unchanged.")
        print(f"Split files saved to: {output_dir}/")

    def _split_single_markdown(self, input_file: str, output_dir: str, heading_level: int = 1,
                             use_heading_names: bool = False) -> List[str]:
        """Split a single markdown file at specified heading level"""
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split content by the specified heading level
        heading_marker = f"{'#' * heading_level} "
        lines = content.split('\n')

        sections = []
        current_section = []
        current_heading = None

        for line in lines:
            if line.startswith(heading_marker):
                # Save previous section if it exists
                if current_heading is not None:
                    sections.append((current_heading, '\n'.join(current_section)))

                # Start new section with this heading
                current_heading = line
                current_section = []
            else:
                # Add line to current section (if we've started a section)
                if current_heading is not None:
                    current_section.append(line)

        # Add the last section if it exists
        if current_heading is not None:
            sections.append((current_heading, '\n'.join(current_section)))

        if not sections:
            return []

        output_files = []
        base_name = Path(input_file).stem

        for i, (heading, section_content) in enumerate(sections):
            # Extract heading text for filename
            heading_text = heading.lstrip('#').strip()
            safe_name = re.sub(r'[^\w\s-]', '', heading_text).strip()
            safe_name = re.sub(r'[-\s]+', '-', safe_name)

            # Truncate filename if too long (limit to 100 characters including extension)
            if len(safe_name) > 90:  # Leave 10 characters for base_name + separator + extension
                safe_name = safe_name[:90]

            if use_heading_names and safe_name:
                filename = f"{safe_name}.md"
            else:
                filename = f"{base_name}_section_{i+1}.md"

            # Always include heading and content
            incremented_content = self._increment_headings(section_content)
            full_content = f"{heading}\n{incremented_content}"

            output_path = os.path.join(output_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            output_files.append(output_path)
            print(f"  → Created: {output_path}")

        return output_files

    def _increment_headings(self, content: str) -> str:
        """Increment all headings in content by one level"""
        return re.sub(
            r'^(#{1,5}) ',
            r'\1# ',
            content,
            flags=re.MULTILINE
        )
