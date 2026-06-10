"""Base command class"""

from abc import ABC, abstractmethod
from typing import Any


class BaseCommand(ABC):
    """Base class for all commands"""

    @abstractmethod
    def execute(self, args) -> Any:
        """Execute the command with given arguments"""
        pass

    @abstractmethod
    def add_arguments(self, parser):
        """Add command-specific arguments to the parser"""
        pass
