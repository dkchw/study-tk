"""Commands package"""

from .base_command import BaseCommand
from .ocr import OCRCommand
from .split_pdf import SplitPDFCommand
from .split_markdown import SplitMarkdownCommand
from .collect_markdown import CollectMarkdownCommand
from .setup import SetupCommand
from .flatten import FlattenCommand
from .toc import TOCCommand
from .remove_empty_lines import RemoveEmptyLinesCommand

__all__ = [
    'BaseCommand',
    'OCRCommand',
    'SplitPDFCommand',
    'SplitMarkdownCommand',
    'CollectMarkdownCommand',
    'SetupCommand',
    'FlattenCommand',
    'TOCCommand',
    'RemoveEmptyLinesCommand',
]
