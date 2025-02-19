"""Module for formatting file contents into prompt-friendly formats.

This module provides functions to detect programming languages based on file extensions
and to format file content in Plaintext, Markdown, or XML formats optimized for LLM prompts.
It now supports additional customization options such as including file boundaries,
truncating content, and appending file metadata.
"""

import os
from typing import Any, Dict

from exceptions import FormatError


def get_language(file_name: str) -> str:
    """Detect the programming language based on the file extension.

    Args:
        file_name (str): The name of the file.

    Returns:
        str: The detected programming language, or an empty string if unknown.
    """
    ext: str = os.path.splitext(file_name)[1].lower()
    mapping: Dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".xml": "xml",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".rb": "ruby",
        ".php": "php",
    }
    return mapping.get(ext, "")


def format_file_content(
    rel_path: str,
    content: str,
    output_format: str,
    options: Dict[str, Any] = None,
) -> str:
    """Format the content of a file according to the specified output format.

    Args:
        rel_path (str): The relative file path.
        content (str): The file content.
        output_format (str): The desired output format ('Plaintext', 'Markdown', 'XML').
        options (Dict[str, Any], optional): Dictionary containing formatting options:
            - include_boundaries (bool): Whether to include file header/footer boundaries.
            - truncate_length (int): Maximum number of characters for content
                (0 means no truncation).
            - file_metadata (Dict[str, Any]): Metadata about the file (e.g., size).
        Defaults to None.

    Returns:
        str: The formatted file content.

    Raises:
        FormatError: If an unsupported format is provided or if formatting fails.
    """
    try:
        valid_formats = frozenset({"Plaintext", "Markdown", "XML"})

        if not isinstance(rel_path, str) or not rel_path.strip():
            raise FormatError("File path must be a non-empty string")
        if not isinstance(content, str):
            raise FormatError("Content must be a string")
        if output_format not in valid_formats:
            raise FormatError(
                f"Unsupported format. Choose from: {', '.join(valid_formats)}"
            )

        options = options or {}
        truncate_length = options.get("truncate_length", 0)
        include_boundaries = options.get("include_boundaries", True)
        file_metadata = options.get("file_metadata")

        if 0 < truncate_length < len(content):
            content = f"{content[:truncate_length]}..."

        metadata_str = (
            f" [Size: {file_metadata['size']} bytes]"
            if file_metadata and "size" in file_metadata
            else ""
        )
        language: str = get_language(rel_path)

        match output_format:
            case "Plaintext":
                if not include_boundaries:
                    return content
                return (
                    f"=== File: {rel_path}{metadata_str} ===\n"
                    f"{content}\n"
                    f"=== End of File: {rel_path} ===\n"
                )

            case "Markdown":
                fence: str = f"```{language}" if language else "```"
                if not include_boundaries:
                    return f"{fence}\n{content}\n```\n"
                return (
                    f"## File: {rel_path}{metadata_str}\n"
                    f"{fence}\n"
                    f"{content}\n"
                    "```\n"
                )

            case "XML":
                lang_attr: str = f' language="{language}"' if language else ""
                if not include_boundaries:
                    return f"<content><![CDATA[{content}]]></content>\n"
                return (
                    f'<file path="{rel_path}"{lang_attr}{metadata_str}>\n'
                    f"  <content><![CDATA[{content}]]></content>\n"
                    f"</file>\n"
                )
    except Exception as e:
        raise FormatError(f"Failed to format content for {rel_path}: {str(e)}") from e
