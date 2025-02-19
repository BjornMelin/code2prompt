"""Module for formatting file contents into prompt-friendly formats.

This module provides functions to detect programming languages based on file extensions
and format file content in Plaintext, Markdown, or XML formats optimized for LLM prompts.
"""

import os
from typing import Any


def get_language(file_name: str) -> str:
    """Detect the programming language based on the file extension.

    Args:
        file_name (str): The name of the file.

    Returns:
        str: The detected programming language.
    """
    ext: str = os.path.splitext(file_name)[1].lower()
    mapping: dict[str, str] = {
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


def format_file_content(rel_path: str, content: str, output_format: str) -> str:
    """Format the content of a file according to the specified output format.

    Args:
        rel_path (str): The relative file path.
        content (str): The file content.
        output_format (str): The desired output format ('Plaintext', 'Markdown', 'XML').

    Returns:
        str: The formatted file content.

    Raises:
        ValueError: If an unsupported format is provided.
    """
    language: str = get_language(rel_path)
    if output_format == "Plaintext":
        return (
            f"=== File: {rel_path} ===\n"
            f"{content}\n"
            f"=== End of File: {rel_path} ===\n"
        )
    elif output_format == "Markdown":
        fence: str = f"```{language}" if language else "```"
        return f"## File: {rel_path}\n" f"{fence}\n" f"{content}\n" "```\n"
    elif output_format == "XML":
        lang_attr: str = f' language="{language}"' if language else ""
        return (
            f'<file path="{rel_path}"{lang_attr}>\n'
            f"  <content><![CDATA[{content}]]></content>\n"
            f"</file>\n"
        )
    else:
        raise ValueError("Unsupported format. Choose from Plaintext, Markdown, or XML.")
