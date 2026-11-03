"""Deprecated pipeline compatibility exports.

Deprecated:
    Import from ``app.services.file_processing`` or its submodules; this module
    only keeps the pre-split helper names importable.
"""
from .parsers.utils import _block, _pages_to_chunks
from .orchestration import _process, parse_document
__all__ = ["_block", "_pages_to_chunks", "_process", "parse_document"]
