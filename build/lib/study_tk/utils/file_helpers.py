"""File helper functions"""

import os
import glob
from pathlib import Path
from typing import List


def find_files(pattern: str, search_path: str = ".") -> List[Path]:
    """Find files matching pattern in search path"""
    files = []
    for file_path in glob.glob(os.path.join(search_path, pattern)):
        files.append(Path(file_path))
    return files


def select_files_interactive(files: List, file_type: str = "file") -> List:
    """Interactive file selection using numbers or questionary"""
    from rich.console import Console
    from rich.table import Table
    import questionary
    console = Console()

    if not files:
        console.print(f"[yellow]No {file_type}s found in current directory.[/yellow]")
        return []

    # Display files with numbers
    table = Table(title=f"Available {file_type}s")
    table.add_column("No.", justify="right", style="cyan", no_wrap=True)
    table.add_column("File Name", style="magenta")
    table.add_column("Size (MB)", justify="right", style="green")

    for idx, f in enumerate(files, start=1):
        label = f.name if isinstance(f, Path) else str(f)
        size_str = "N/A"
        if isinstance(f, Path) and f.exists():
            size_mb = f.stat().st_size / (1024 * 1024)
            size_str = f"{size_mb:.2f}"
        table.add_row(str(idx), label, size_str)

    console.print(table)

    console.print("\n[bold]Selection Options:[/bold]")
    console.print("  - Type a [cyan]number[/cyan] to select one file")
    console.print("  - Type [cyan]'all'[/cyan] to process all files")
    console.print("  - Type [cyan]multiple numbers[/cyan] separated by commas (e.g., 1,3,5)")
    console.print("  - Press [cyan]Enter[/cyan] without typing to use interactive checkbox")
    
    user_input = questionary.text("Your choice:").ask()

    if not user_input or user_input.strip() == "":
        # Fallback to interactive checkbox if user just pressed Enter
        choices = []
        for f in files:
            label = f.name if isinstance(f, Path) else str(f)
            choices.append(questionary.Choice(title=label, value=f))

        selected = questionary.checkbox(
            f"Select {file_type}s to process:",
            choices=choices,
            instruction="(Use space to select, enter to confirm)"
        ).ask()
        return selected or []

    user_input = user_input.strip().lower()

    if user_input == "all":
        return files
    
    selected_files = []
    try:
        indices = [int(x.strip()) for x in user_input.split(",")]
        for idx in indices:
            if 1 <= idx <= len(files):
                selected_files.append(files[idx - 1])
            else:
                console.print(f"[yellow]Warning: Invalid number {idx} (out of range)[/yellow]")
    except ValueError:
        console.print("[red]Invalid input. Please enter numbers separated by commas, 'all', or leave empty for checkbox.[/red]")
        return []

    return selected_files
