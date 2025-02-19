"""Configuration module for Code2Prompt Streamlit App.

This module contains default configuration settings for the project, including default
directories/files to ignore during prompt generation and default file type filters.

Attributes:
    DEFAULT_IGNORE_DIRS (List[str]): List of directory names to ignore.
    DEFAULT_FILE_TYPES (List[str]): Default list of file extensions to process.
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

DEFAULT_FILE_TYPES: List[str] = [
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".html",
    ".css",
    ".json",
    ".xml",
    ".md",
    ".yml",
    ".yaml",
    ".rb",
    ".php",
]
