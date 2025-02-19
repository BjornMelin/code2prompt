"""Module for processing ZIP files and retrieving file paths.

This module provides functions to extract ZIP files into a temporary directory
and retrieve all file paths recursively while ignoring specified directories.
"""

import os
import zipfile
import tempfile
import shutil
from typing import List, Set, Optional

from config import DEFAULT_IGNORE_DIRS
from exceptions import FileProcessingError, TempFileError


def extract_zip(zip_path: str) -> str:
    """Extract the provided ZIP file into a temporary directory.

    Args:
        zip_path (str): The path to the ZIP file.

    Returns:
        str: The path to the temporary directory containing the extracted files.

    Raises:
        FileProcessingError: If the ZIP file is invalid or corrupted.
        TempFileError: If there's an error creating or accessing temporary directory.
    """
    try:
        temp_dir: str = tempfile.mkdtemp()
    except OSError as e:
        raise TempFileError(f"Failed to create temporary directory: {e}") from e

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
    except zipfile.BadZipFile as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise FileProcessingError(f"Invalid or corrupted ZIP file: {e}") from e
    except OSError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise TempFileError(
            f"Failed to extract files to temporary directory: {e}"
        ) from e

    return temp_dir


def get_files_from_directory(
    base_dir: str,
    ignore_dirs: Optional[Set[str]] = None,
    file_types: Optional[Set[str]] = None,
) -> List[str]:
    """Retrieve a list of file paths from a directory, excluding ignored directories,
    and optionally filtering by file types.

    Args:
        base_dir (str): The base directory to search for files.
        ignore_dirs (Set[str], optional): A set of directory names to ignore.
            Defaults to DEFAULT_IGNORE_DIRS.
        file_types (Set[str], optional): A set of file extensions to include.
            If None, all files are included.

    Returns:
        List[str]: A list of file paths.

    Raises:
        FileProcessingError: If there's an error accessing or reading the directory.
    """
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)

    try:
        files_list: List[str] = []
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if file_types:
                    ext = os.path.splitext(file)[1].lower()
                    if ext not in file_types:
                        continue
                file_path: str = os.path.join(root, file)
                files_list.append(file_path)
        return files_list
    except OSError as e:
        raise FileProcessingError(f"Failed to read directory {base_dir}: {e}") from e
