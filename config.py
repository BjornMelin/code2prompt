"""Configuration module for Code2Prompt Streamlit App.

This module contains default configuration settings for the project,
including the default directories and files to ignore during prompt generation.

Attributes:
    DEFAULT_IGNORE_DIRS (List[str]): List of directory names to ignore.
"""

from typing import List

DEFAULT_IGNORE_DIRS: List[str] = [
    "node_modules",
    ".next",
    ".bolt",
    ".git",
    "dist",
    "build",
    "tmp",
    "coverage",
    "venv",
    ".cache",
    "logs",
    "out",
]
