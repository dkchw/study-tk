"""Directory flatten command implementation"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple

from study_tk.core.base_tool import BaseTool
from study_tk.commands.base_command import BaseCommand


class FlattenCommand(BaseCommand, BaseTool):
    """Directory flattening command"""

    def __init__(self):
        BaseTool.__init__(self)

    def execute(self, args):
        """Execute flatten command"""
        self.flatten_directory(
            args.path,
            args.levels,
            args.include_patterns,
            args.exclude_patterns,
            args.duplicate_handling
        )

    def add_arguments(self, parser):
        """Add flatten-specific arguments"""
        parser.add_argument('--path', '-p', default='.',
                           help='Path to flatten (default: current directory)')
        parser.add_argument('--levels', '-l', type=int, default=1,
                           help='Number of directory levels to flatten (default: 1)')
        parser.add_argument('--include-patterns', '-i', nargs='+', default=['*'],
                           help='File patterns to include (default: *)')
        parser.add_argument('--exclude-patterns', '-e', nargs='+', default=[],
                           help='File patterns to exclude')
        parser.add_argument('--duplicate-handling', '-d', choices=['ask', 'skip', 'overwrite', 'rename'],
                           default='ask',
                           help="How to handle duplicate files: 'ask' (prompt for each), 'skip' (skip duplicates), 'overwrite' (replace existing), 'rename' (add suffix) (default: 'ask')")

    def flatten_directory(self, path: str, levels: int = 1, include_patterns: List[str] = ['*'],
                         exclude_patterns: List[str] = [], duplicate_handling: str = 'ask'):
        """Flatten directory structure by moving files from subdirectories to current directory"""
        path = Path(path)

        if not path.exists():
            print(f"Error: Path '{path}' does not exist")
            return

        if not path.is_dir():
            print(f"Error: Path '{path}' is not a directory")
            return

        print(f"\nFlattening directory: {path}")
        print(f"Levels to flatten: {levels}")
        print(f"Include patterns: {include_patterns}")
        print(f"Exclude patterns: {exclude_patterns}")
        print(f"Duplicate handling: {duplicate_handling}")

        # Find all files to move
        files_to_move = self._find_files_to_move(path, levels, include_patterns, exclude_patterns)

        if not files_to_move:
            print("No files found to flatten.")
            return

        print(f"\nFound {len(files_to_move)} files to move:")
        for src_path, dest_path in files_to_move:
            print(f"  {src_path} -> {dest_path}")

        # Confirm before proceeding
        confirm = input(f"\nProceed with flattening {len(files_to_move)} files? (y/N): ").lower()
        if confirm != 'y':
            print("Flattening cancelled.")
            return

        # Process files
        moved_count = 0
        skipped_count = 0

        for src_path, dest_path in files_to_move:
            if dest_path.exists():
                # Handle duplicate
                if duplicate_handling == 'skip':
                    print(f"  → Skipped (exists): {dest_path.name}")
                    skipped_count += 1
                    continue
                elif duplicate_handling == 'overwrite':
                    print(f"  → Overwriting: {dest_path.name}")
                    dest_path.unlink()
                    self._move_file(src_path, dest_path)
                    moved_count += 1
                elif duplicate_handling == 'rename':
                    # Add suffix to avoid overwriting
                    dest_path = self._get_unique_filename(dest_path)
                    print(f"  → Renaming to: {dest_path.name}")
                    self._move_file(src_path, dest_path)
                    moved_count += 1
                elif duplicate_handling == 'ask':
                    # Interactive handling
                    print(f"\nDuplicate found: {dest_path.name}")
                    print("1. Skip")
                    print("2. Overwrite")
                    print("3. Rename")

                    while True:
                        choice = input("Choose action (1-3): ").strip()
                        if choice == '1':
                            print(f"  → Skipped: {dest_path.name}")
                            skipped_count += 1
                            break
                        elif choice == '2':
                            print(f"  → Overwriting: {dest_path.name}")
                            dest_path.unlink()
                            self._move_file(src_path, dest_path)
                            moved_count += 1
                            break
                        elif choice == '3':
                            new_dest_path = self._get_unique_filename(dest_path)
                            print(f"  → Renaming to: {new_dest_path.name}")
                            self._move_file(src_path, new_dest_path)
                            moved_count += 1
                            break
                        else:
                            print("Invalid choice. Please enter 1, 2, or 3.")
            else:
                # No duplicate, move normally
                self._move_file(src_path, dest_path)
                print(f"  → Moved: {dest_path.name}")
                moved_count += 1

        print(f"\n✓ Flattening complete!")
        print(f"  - Moved: {moved_count} files")
        print(f"  - Skipped: {skipped_count} files")

    def _find_files_to_move(self, path: Path, levels: int, include_patterns: List[str],
                           exclude_patterns: List[str]) -> List[Tuple[Path, Path]]:
        """Find files to move based on levels and patterns"""
        files_to_move = []

        # Walk through directories up to specified levels
        for current_path, dirs, files in os.walk(path):
            # Calculate current depth relative to starting path
            current_depth = len(current_path.split(os.sep)) - len(str(path).split(os.sep))

            # Stop if we've reached the max levels
            if current_depth >= levels:
                dirs.clear()  # Don't go deeper
                continue

            # Process files in current directory
            for file in files:
                src_path = Path(current_path) / file

                # Check include patterns
                should_include = False
                for pattern in include_patterns:
                    if src_path.match(pattern) or src_path.name == pattern:
                        should_include = True
                        break

                if not should_include:
                    continue

                # Check exclude patterns
                should_exclude = False
                for pattern in exclude_patterns:
                    if src_path.match(pattern) or src_path.name == pattern:
                        should_exclude = True
                        break

                if should_exclude:
                    continue

                # Add to files to move
                dest_name = src_path.name
                dest_path = path / dest_name
                files_to_move.append((src_path, dest_path))

        return files_to_move

    def _move_file(self, src_path: Path, dest_path: Path):
        """Move a file from source to destination"""
        try:
            shutil.move(str(src_path), str(dest_path))
        except Exception as e:
            print(f"  → Error moving {src_path.name}: {str(e)}")

    def _get_unique_filename(self, path: Path) -> Path:
        """Get a unique filename by adding a suffix if needed"""
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
