"""Setup command implementation"""

from pathlib import Path

from study_tk.core.base_tool import BaseTool
from study_tk.commands.base_command import BaseCommand
from study_tk.core.config import save_mistral_api_key, save_zai_api_key


class SetupCommand(BaseCommand, BaseTool):
    """Setup command for API keys"""

    def __init__(self):
        BaseTool.__init__(self)

    def execute(self, args):
        """Execute setup command"""
        self.setup_api_keys()

    def add_arguments(self, parser):
        """Add setup-specific arguments (none needed)"""
        pass

    def setup_api_keys(self):
        """Interactive setup for API keys using rich and questionary"""
        import questionary
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        
        console = Console()
        
        config_dir = Path.home() / ".config" / "study-tk"
        config_file = config_dir / "config"

        console.print(Panel.fit(
            f"API Key Setup\n[dim]Config: {config_file}[/dim]",
            border_style="cyan"
        ))

        mistral_key = questionary.password("Enter your Mistral API key (press Enter to skip):").ask()
        if mistral_key:
            if save_mistral_api_key(mistral_key):
                console.print("[green]✓ Mistral API key saved[/green]")
            else:
                console.print("[red]✗ Failed to save Mistral API key[/red]")

        zai_key = questionary.password("Enter your ZAI API key (press Enter to skip):").ask()
        if zai_key:
            if save_zai_api_key(zai_key):
                console.print("[green]✓ ZAI API key saved[/green]")
            else:
                console.print("[red]✗ Failed to save ZAI API key[/red]")

        console.print("\n[bold green]Setup complete![/bold green] You can now use the OCR feature.")
        return True
