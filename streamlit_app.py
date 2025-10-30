"""Streamlit app for Code2Prompt.

This module provides a web-based interface using Streamlit to transform one or more ZIP files
containing codebases into structured, prompt-optimized formats for language models.
Users can select directories to ignore, filter file types, choose an output format, and customize
various aspects of the generated prompt.

Usage:
    Run the app using:
        streamlit run streamlit_app.py
"""

import fnmatch

# Standard library imports
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass

# pylint: disable=deprecated-module
from formatter import format_file_content
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Third-party imports
import streamlit as st
import tiktoken

# Local application/library-specific imports
from config import DEFAULT_FILE_TYPES, DEFAULT_IGNORE_DIRS
from exceptions import FileProcessingError, FormatError, TempFileError
from file_processor import extract_zip, get_files_from_directory


@dataclass
class FileFilterConfig:
    """Configuration for file filtering."""

    ignore_dirs: Set[str]
    ignore_patterns: Set[str]
    file_types: Set[str]
    selected_files: Optional[Set[str]] = None


@dataclass
class FormatConfig:
    """Configuration for output formatting."""

    output_format: str
    options: Dict[str, Any]


@dataclass
class UploadProcessingConfig:
    """Configuration for upload processing."""

    temp_zip_paths: List[str]
    ignore_dirs: Set[str]
    ignore_patterns: Set[str]
    output_format: str
    format_options: Dict[str, Any]
    file_types: Set[str]
    selected_files: Optional[Set[str]] = None


@dataclass
class ProcessingConfig:
    """Combined configuration for prompt generation."""

    zip_files: List[str]
    ignore_dirs: Set[str]
    ignore_patterns: Set[str]
    output_format: str
    format_options: Dict[str, Any]
    file_types: Set[str]
    selected_files: Optional[Set[str]]


def count_tokens(text: str) -> int:
    """Count the number of tokens in the text using GPT-3 tokenizer.

    Args:
        text (str): The text to count tokens for.

    Returns:
        int: Number of tokens in the text.
    """
    try:
        encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        return len(encoding.encode(text))
    except (KeyError, ValueError, ImportError):
        # Fallback to approximate token count if tiktoken fails or is not available
        return len(text.split())


def should_ignore_file(path: str, ignore_patterns: Set[str]) -> bool:
    """Check if a file should be ignored based on patterns.

    Args:
        path (str): The file path to check.
        ignore_patterns (Set[str]): Set of glob patterns to match against.

    Returns:
        bool: True if the file should be ignored, False otherwise.
    """
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def handle_file_upload(multi: bool = True) -> List[str]:
    """Handle file upload and save each file to a temporary location.

    Args:
        multi (bool): If True, allow multiple files.

    Returns:
        List[str]: A list of paths to the temporary ZIP files.
    """
    uploaded_files = st.file_uploader(
        "📁 Upload ZIP file(s)", type="zip", accept_multiple_files=multi
    )
    temp_paths: List[str] = []
    if not uploaded_files:
        return temp_paths

    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]

    for uploaded_file in uploaded_files:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                st.info(f"File **{uploaded_file.name}** uploaded successfully!")
                temp_paths.append(tmp_file.name)
        except (IOError, OSError) as e:
            st.error(f"Failed to save uploaded file {uploaded_file.name}: {e}")
    return temp_paths


def process_files(
    file_paths: List[str], temp_dir: str, format_config: FormatConfig
) -> Tuple[List[str], List[str]]:
    """Process individual files and format their content.

    Args:
        file_paths (List[str]): List of file paths to process.
        temp_dir (str): Temporary directory containing the files.
        format_config (FormatConfig): Configuration for output formatting.

    Returns:
        Tuple[List[str], List[str]]: A tuple containing:
            - A list of formatted prompt lines.
            - A file tree as a list of relative file paths.
    """
    prompt_lines: List[str] = [
        "Below is the structured project codebase extracted from the provided ZIP file:\n"
    ]
    file_tree: List[str] = []
    for file_path in file_paths:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            st.warning(f"Skipping binary file: {file_path}")
            continue
        except IOError as e:
            st.warning(f"Could not read file {file_path}: {e}")
            continue

        rel_path: str = os.path.relpath(file_path, temp_dir)
        file_tree.append(rel_path)
        try:
            formatted: str = format_file_content(
                rel_path, content, format_config.output_format, format_config.options
            )
            prompt_lines.append(formatted)
        except (ValueError, KeyError, TypeError) as e:
            raise FormatError(f"Failed to format {rel_path}: {e}") from e
    return prompt_lines, file_tree


def list_files_in_zip(zip_path: str) -> Optional[List[str]]:
    """List all files in a ZIP archive.

    Args:
        zip_path (str): Path to the ZIP file.

    Returns:
        Optional[List[str]]: List of file paths in the ZIP, or None if error.
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            return zip_ref.namelist()
    except (zipfile.BadZipFile, OSError) as e:
        st.error(f"Failed to read ZIP file: {e}")
        return None


@st.cache_data(show_spinner=False)
def process_zip_file(
    temp_zip_path: str,
    file_filter: FileFilterConfig,
    format_config: FormatConfig,
) -> Tuple[str, List[str]]:
    """Process a ZIP file and generate the formatted prompt text and file tree preview.

    Args:
        temp_zip_path (str): Path to the temporary ZIP file.
        file_filter (FileFilterConfig): Configuration for file filtering.
        format_config (FormatConfig): Configuration for output formatting.

    Returns:
        Tuple[str, List[str]]: A tuple containing:
            - Combined prompt text.
            - File tree as a list of relative file paths.

    Raises:
        FileProcessingError: If there's an error with the ZIP file.
        TempFileError: If there's an error with temporary file handling.
    """
    try:
        temp_dir: str = extract_zip(temp_zip_path)
    except zipfile.BadZipFile as e:
        raise FileProcessingError(f"Invalid or corrupted ZIP file: {e}") from e
    except OSError as e:
        raise TempFileError(
            f"Failed to create or access temporary directory: {e}"
        ) from e

    try:
        # Combine ignore dirs and patterns
        all_ignores = file_filter.ignore_dirs.union(file_filter.ignore_patterns)
        file_paths: List[str] = get_files_from_directory(
            temp_dir, all_ignores, file_filter.file_types
        )

        # Filter by selected files if specified
        if file_filter.selected_files is not None:
            file_paths = [
                path
                for path in file_paths
                if os.path.relpath(path, temp_dir) in file_filter.selected_files
            ]

        prompt_lines, file_tree = process_files(file_paths, temp_dir, format_config)
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except OSError as e:
            st.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")

    return "\n".join(prompt_lines), file_tree


def _process_single_zip(
    temp_zip_path: str,
    processing_args: Tuple[FileFilterConfig, FormatConfig],
    progress_info: Tuple[int, int],
) -> Tuple[str, List[str], List[str]]:
    """Process a single ZIP file and return its results.

    Args:
        temp_zip_path (str): Path to the ZIP file.
        processing_args: Tuple containing (file_filter, format_config)
        progress_info: Tuple containing (current_index, total_files).

    Returns:
        Tuple containing (prompt_text, file_tree, log_messages) for this ZIP file.
    """
    idx, total = progress_info
    file_filter, format_config = processing_args
    log_messages: List[str] = []

    try:
        with st.spinner(f"Processing file {idx + 1} of {total}..."):
            prompt_text, file_tree = process_zip_file(
                temp_zip_path,
                file_filter,
                format_config,
            )
        log_messages.append(f"Processed {Path(temp_zip_path).name} successfully.")
        return prompt_text, file_tree, log_messages
    except (FileProcessingError, FormatError, TempFileError, OSError) as e:
        log_messages.append(f"Error processing {Path(temp_zip_path).name}: {e}")
        return "", [], log_messages
    finally:
        try:
            Path(temp_zip_path).unlink(missing_ok=True)
        except OSError as e:
            log_messages.append(f"Failed to remove temporary file {temp_zip_path}: {e}")


def process_uploads(config: UploadProcessingConfig) -> Tuple[str, List[str], List[str]]:
    """Process multiple uploaded ZIP files and generate combined prompt text.

    Args:
        config (UploadProcessingConfig): Configuration for processing uploads.

    Returns:
        Tuple[str, List[str], List[str]]: A tuple containing:
            - Combined prompt text from all processed ZIP files.
            - Combined file tree as a list of relative file paths.
            - Log messages from processing steps.
    """
    file_filter = FileFilterConfig(
        config.ignore_dirs,
        config.ignore_patterns,
        config.file_types,
        config.selected_files,
    )
    format_config = FormatConfig(config.output_format, config.format_options)
    processing_args = (file_filter, format_config)

    results: List[Tuple[str, List[str], List[str]]] = []
    progress_bar = st.progress(0)
    total_files = len(config.temp_zip_paths)

    for idx, path in enumerate(config.temp_zip_paths):
        result = _process_single_zip(path, processing_args, (idx, total_files))
        results.append(result)
        progress_bar.progress((idx + 1) / total_files)

    # Combine results
    all_prompts, all_trees, all_logs = zip(*results) if results else ([], [], [])
    return (
        "\n\n".join(filter(None, all_prompts)),
        [item for sublist in all_trees for item in sublist],
        [item for sublist in all_logs for item in sublist],
    )


def setup_sidebar_options() -> Tuple[Set[str], Set[str], str, Dict[str, Any], Set[str]]:
    """Set up and retrieve sidebar options for the app.

    Returns:
        Tuple[Set[str], Set[str], str, Dict[str, Any], Set[str]]:
            - ignore_dirs: Directory names to ignore.
            - ignore_patterns: Custom patterns to ignore.
            - output_format: Selected output format.
            - format_options: Formatting options.
            - file_types: Allowed file types.
    """
    st.sidebar.header("Settings")

    # Ignore Settings
    st.sidebar.subheader("Ignore Settings")
    ignore_dirs: Set[str] = set(
        st.sidebar.multiselect(
            "Select directories to ignore:",
            options=DEFAULT_IGNORE_DIRS,
            default=DEFAULT_IGNORE_DIRS,
            help="Common directories to exclude (e.g., node_modules, .git).",
        )
    )

    custom_ignores: str = st.sidebar.text_area(
        "Add custom ignore patterns:",
        value="",
        help="Enter patterns to ignore, one per line. Wildcards (*) are supported.",
        placeholder="*.pyc\n__pycache__/*\n.env",
    )
    ignore_patterns: Set[str] = {
        pattern.strip() for pattern in custom_ignores.split("\n") if pattern.strip()
    }

    # Output Format
    st.sidebar.subheader("Prompt Format")
    output_format: str = st.sidebar.selectbox(
        "Select Output Format:",
        options=["Plaintext", "Markdown", "XML", "JSON"],
        help="Choose how the generated prompt is structured.",
    )

    # Advanced Format Options
    include_boundaries: bool = st.sidebar.checkbox(
        "Include file boundaries",
        value=True,
        help="Include headers/footers for each file.",
    )
    truncate_length: int = st.sidebar.number_input(
        "Truncate file content (max characters):",
        min_value=0,
        value=0,
        step=100,
        help="Set to 0 for no truncation.",
    )
    include_metadata: bool = st.sidebar.checkbox(
        "Include file metadata",
        value=False,
        help="Include file size metadata in the prompt.",
    )
    format_options: Dict[str, Any] = {
        "include_boundaries": include_boundaries,
        "truncate_length": truncate_length,
        "file_metadata": {"size": None} if include_metadata else None,
    }

    # File Types
    st.sidebar.subheader("File Types")
    file_types_selected: List[str] = st.sidebar.multiselect(
        "Filter by file types (extensions):",
        options=DEFAULT_FILE_TYPES,
        default=DEFAULT_FILE_TYPES,
        help="Select the file types you want to process.",
    )
    file_types: Set[str] = {ft.lower() for ft in file_types_selected}

    return ignore_dirs, ignore_patterns, output_format, format_options, file_types


def handle_prompt_generation(
    config: ProcessingConfig,
) -> Tuple[str, List[str], List[str]]:
    """Handle the prompt generation process."""
    upload_config = UploadProcessingConfig(
        temp_zip_paths=config.zip_files,
        ignore_dirs=config.ignore_dirs,
        ignore_patterns=config.ignore_patterns,
        output_format=config.output_format,
        format_options=config.format_options,
        file_types=config.file_types,
        selected_files=config.selected_files,
    )
    return process_uploads(upload_config)


def init_session_state() -> None:
    """Initialize session state variables."""
    for key in [
        "prompt_text",
        "file_tree",
        "token_count",
        "zip_files",
        "selected_files",
    ]:
        if key not in st.session_state:
            st.session_state[key] = [] if key in ["file_tree", "zip_files"] else ""


def handle_file_selection() -> Tuple[List[str], Optional[Set[str]]]:
    """Handle file upload and selection."""
    cols = st.columns([2, 1])
    with cols[0]:
        temp_zip_paths = handle_file_upload(multi=True)
        selected_files = None

        if temp_zip_paths:
            st.session_state.zip_files = temp_zip_paths
            all_files = []
            for zip_path in temp_zip_paths:
                files = list_files_in_zip(zip_path)
                if files:
                    all_files.extend(files)

            if all_files:
                st.session_state.selected_files = st.multiselect(
                    "Select files to include in prompt:",
                    options=all_files,
                    default=all_files,
                    help="Select specific files to include in the prompt generation.",
                )
                selected_files = set(st.session_state.selected_files)

    return temp_zip_paths, selected_files


def display_metrics(prompt_text: str, file_tree: List[str]) -> None:
    """Display metrics about the generated prompt.

    Args:
        prompt_text (str): The generated prompt text
        file_tree (List[str]): List of processed files
    """
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Files Processed", len(file_tree))
    with col2:
        token_count = count_tokens(prompt_text)
        st.metric("Estimated Tokens", token_count)


def display_generated_prompt(config: ProcessingConfig) -> None:
    """Display the generated prompt and metrics."""
    combined_prompt, combined_file_tree, log_messages = handle_prompt_generation(config)

    custom_header = st.sidebar.text_input(
        "Custom Prompt Header:",
        value="",
        help="Optional custom header to include at the top of the generated prompt.",
    )
    final_prompt = (
        f"{custom_header.strip()}\n" if custom_header.strip() else "" + combined_prompt
    )

    display_metrics(final_prompt, combined_file_tree)
    st.success("Prompt generated successfully!")
    st.text_area("Generated Prompt", value=final_prompt, height=500)
    st.text("\n".join(log_messages))


def main() -> None:
    """Main function to run the Code2Prompt Streamlit app."""
    st.set_page_config(page_title="Code2Prompt 🚀", layout="wide")
    st.title("Code2Prompt 🚀")
    st.markdown(
        "Transform your codebase into a structured, prompt-optimized format for LLMs like ChatGPT. "
        "Upload ZIP file(s) and customize your settings for optimal results."
    )

    # Initialize session state
    init_session_state()

    _, selected_files = handle_file_selection()

    # Retrieve sidebar options
    ignore_dirs, ignore_patterns, output_format, format_options, file_types = (
        setup_sidebar_options()
    )
    generate_button: bool = st.sidebar.button("🔄 Generate Prompt")

    if st.session_state.zip_files and generate_button:
        config = ProcessingConfig(
            zip_files=st.session_state.zip_files,
            ignore_dirs=ignore_dirs,
            ignore_patterns=ignore_patterns,
            output_format=output_format,
            format_options=format_options,
            file_types=file_types,
            selected_files=selected_files,
        )
        display_generated_prompt(config)

    # Show file tree preview
    if st.checkbox("Show file tree preview") and st.session_state.file_tree:
        with st.expander("File Tree Preview"):
            st.write(f"Total files: {len(st.session_state.file_tree)}")
            for rel_path in st.session_state.file_tree:
                st.write(rel_path)


if __name__ == "__main__":
    main()
