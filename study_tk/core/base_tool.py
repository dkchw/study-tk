"""Base class for all tools"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


class BaseTool(ABC):
    """Base class for all study toolkit operations"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self, *args, **kwargs):
        """Execute the tool operation"""
        pass

    def validate_inputs(self, files: List[Path]) -> List[Path]:
        """Validate input files exist and are accessible"""
        valid_files = []
        for file_path in files:
            if file_path.exists():
                valid_files.append(file_path)
            else:
                print(f"Warning: File not found: {file_path}")
        return valid_files
