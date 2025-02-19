"""Custom exceptions for the Code2Prompt application.

This module defines custom exception classes used throughout the Code2Prompt
application for better error handling and reporting.
"""


class Code2PromptError(Exception):
    """Base exception class for Code2Prompt application."""


class FileProcessingError(Code2PromptError):
    """Exception raised when there's an error processing a file.

    This can occur during file reading, parsing, or any other file-related operations.
    """


class TempFileError(Code2PromptError):
    """Exception raised when there's an error handling temporary files.

    This includes errors creating, writing to, or cleaning up temporary files and directories.
    """


class FormatError(Code2PromptError):
    """Exception raised when there's an error formatting file content.

    This occurs when the application fails to format file content into the requested output format.
    """
