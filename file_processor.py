"""Module for processing ZIP files and retrieving file paths.

This module provides functions to extract ZIP files into temporary directories
and retrieve all file paths recursively while ignoring specified directories.
"""

import os
import zipfile
import tempfile
import shutil
from typing import List, Set

from config import DEFAULT_IGNORE_DIRS


def extract_zip(zip_path: str) -> str:
    """Extract the provided ZIP file into a temporary directory.

    Args:
        zip_path (str): The path to the ZIP file.

    Returns:
        str: The path to the temporary directory containing the extracted files.

    Raises:
        Exception: If the ZIP extraction fails.
    """
    temp_dir: str = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
    except Exception as e:
        shutil.rmtree(temp_dir)
        raise Exception(f"Failed to extract ZIP file: {e}")
    return temp_dir


def get_files_from_directory(base_dir: str, ignore_dirs: Set[str] = None) -> List[str]:
    """Retrieve a list of file paths from a directory, excluding ignored directories.

    Args:
        base_dir (str): The base directory to search for files.
        ignore_dirs (Set[str], optional): A set of directory names to ignore. Defaults to None.

    Returns:
        List[str]: A list of file paths.
    """
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)
    files_list: List[str] = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            file_path = os.path.join(root, file)
            files_list.append(file_path)
    return files_list
