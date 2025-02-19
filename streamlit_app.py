"""Streamlit app for Code2Prompt.

This module provides a web-based interface using Streamlit to transform one or more ZIP files
containing codebases into structured, prompt-optimized formats for language models.
Users can select directories to ignore, filter file types, choose an output format, and customize
various aspects of the generated prompt.

Usage:
    Run the app using:
        streamlit run streamlit_app.py
"""

# Standard library imports
import os
import shutil
import tempfile
import zipfile

# pylint: disable=deprecated-module
from formatter import format_file_content
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Third-party imports
import streamlit as st

# Local application/library-specific imports
from config import DEFAULT_IGNORE_DIRS, DEFAULT_FILE_TYPES
from exceptions import FileProcessingError, FormatError, TempFileError
from file_processor import extract_zip, get_files_from_directory


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
    file_paths: List[str], temp_dir: str, output_format: str, options: Dict[str, Any]
) -> Tuple[List[str], List[str]]:
    """Process individual files and format their content.

    Args:
        file_paths (List[str]): List of file paths to process.
        temp_dir (str): Temporary directory containing the files.
        output_format (str): Desired output format ('Plaintext', 'Markdown', 'XML', 'JSON').
        options (Dict[str, Any]): Formatting options to pass to formatter.

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
                rel_path, content, output_format, options
            )
            prompt_lines.append(formatted)
        except Exception as e:
            raise FormatError(f"Failed to format {rel_path}: {e}") from e
    return prompt_lines, file_tree


@st.cache_data(show_spinner=False)
def process_zip_file(
    temp_zip_path: str,
    ignore_options: Set[str],
    output_format: str,
    options: Dict[str, Any],
    file_types: Set[str],
) -> Tuple[str, List[str]]:
    """Process a ZIP file and generate the formatted prompt text and file tree preview.

    Args:
        temp_zip_path (str): Path to the temporary ZIP file.
        ignore_options (Set[str]): Directories/files to ignore.
        output_format (str): Desired output format.
        options (Dict[str, Any]): Additional formatting options.
        file_types (Set[str]): Allowed file types.

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
        file_paths: List[str] = get_files_from_directory(
            temp_dir, ignore_options, file_types
        )
        prompt_lines, file_tree = process_files(
            file_paths, temp_dir, output_format, options
        )
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except OSError as e:
            st.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")

    return "\n".join(prompt_lines), file_tree


def _process_single_zip(
    temp_zip_path: str,
    processing_args: Tuple[Set[str], str, Dict[str, Any], Set[str]],
    progress_info: Tuple[int, int],
) -> Tuple[str, List[str], List[str]]:
    """Process a single ZIP file and return its results.

    Args:
        temp_zip_path (str): Path to the ZIP file.
        processing_args: Tuple containing
            - ignore_options
            - output_format
            = format_options
            - file_types.
        progress_info: Tuple containing (current_index, total_files).

    Returns:
        Tuple containing (prompt_text, file_tree, log_messages) for this ZIP file.
    """
    idx, total = progress_info
    ignore_options, output_format, format_options, file_types = processing_args
    log_messages: List[str] = []

    try:
        with st.spinner(f"Processing file {idx+1} of {total}..."):
            prompt_text, file_tree = process_zip_file(
                temp_zip_path,
                ignore_options,
                output_format,
                format_options,
                file_types,
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


def process_uploads(
    temp_zip_paths: List[str],
    ignore_options: Set[str],
    output_format: str,
    format_options: Dict[str, Any],
    file_types: Set[str],
) -> Tuple[str, List[str], List[str]]:
    """Process multiple uploaded ZIP files and generate combined prompt text.

    Args:
        temp_zip_paths (List[str]): List of temporary ZIP file paths.
        ignore_options (Set[str]): Directories/files to ignore.
        output_format (str): Desired output format.
        format_options (Dict[str, Any]): Formatting options.
        file_types (Set[str]): Allowed file types.

    Returns:
        Tuple[str, List[str], List[str]]: A tuple containing:
            - Combined prompt text from all processed ZIP files.
            - Combined file tree as a list of relative file paths.
            - Log messages from processing steps.
    """
    processing_args = (ignore_options, output_format, format_options, file_types)
    results: List[Tuple[str, List[str], List[str]]] = []
    progress_bar = st.progress(0)
    total_files = len(temp_zip_paths)

    for idx, path in enumerate(temp_zip_paths):
        result = _process_single_zip(path, processing_args, (idx + 1, total_files))
        results.append(result)
        progress_bar.progress((idx + 1) / total_files)

    # Combine results
    all_prompts, all_trees, all_logs = zip(*results) if results else ([], [], [])
    return (
        "\n\n".join(filter(None, all_prompts)),
        [item for sublist in all_trees for item in sublist],
        [item for sublist in all_logs for item in sublist],
    )


def setup_sidebar_options() -> Tuple[Set[str], str, Dict[str, Any], Set[str]]:
    """Set up and retrieve sidebar options for the app.

    Returns:
        Tuple[Set[str], str, Dict[str, Any], Set[str]]:
            - ignore_options: Directories/files to ignore.
            - output_format: Selected output format.
            - format_options: Formatting options.
            - file_types: Allowed file types.
    """
    st.sidebar.header("Settings")

    # Ignore Settings
    st.sidebar.subheader("Ignore Settings")
    ignore_options: Set[str] = set(
        st.sidebar.multiselect(
            "Select directories/files to ignore:",
            options=DEFAULT_IGNORE_DIRS,
            default=DEFAULT_IGNORE_DIRS,
            help="Common directories to exclude (e.g., node_modules, .git).",
        )
    )
    custom_ignore: str = st.sidebar.text_input(
        "Add custom ignore pattern (comma-separated):",
        value="",
        help="Enter additional directories/files to ignore, separated by commas.",
    )
    if custom_ignore.strip():
        custom_list: Set[str] = {
            x.strip() for x in custom_ignore.split(",") if x.strip()
        }
        ignore_options.update(custom_list)

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

    return ignore_options, output_format, format_options, file_types


def main() -> None:
    """Main function to run the Code2Prompt Streamlit app."""
    st.set_page_config(page_title="Code2Prompt 🚀", layout="wide")
    st.title("Code2Prompt 🚀")
    st.markdown(
        "Transform your codebase into a structured, prompt-optimized format for LLMs like ChatGPT. "
        "Upload ZIP file(s) and customize your settings for optimal results."
    )

    # Initialize session state for prompt and file tree preview.
    if "prompt_text" not in st.session_state:
        st.session_state["prompt_text"] = ""
    if "file_tree" not in st.session_state:
        st.session_state["file_tree"] = []

    # Retrieve sidebar options.
    ignore_options, output_format, format_options, file_types = setup_sidebar_options()
    generate_button: bool = st.sidebar.button("🔄 Generate Prompt")

    # Handle file uploads.
    temp_zip_paths: List[str] = handle_file_upload(multi=True)
    log_placeholder = st.empty()

    if temp_zip_paths and generate_button:
        combined_prompt: str
        combined_file_tree: List[str]
        log_messages: List[str]
        combined_prompt, combined_file_tree, log_messages = process_uploads(
            temp_zip_paths, ignore_options, output_format, format_options, file_types
        )

        custom_header: str = st.sidebar.text_input(
            "Custom Prompt Header:",
            value="",
            help="Optional custom header to include at the top of the generated prompt.",
        )
        final_prompt: str = (
            f"{custom_header.strip()}\n" if custom_header.strip() else ""
        ) + combined_prompt

        st.session_state["prompt_text"] = final_prompt
        st.session_state["file_tree"] = combined_file_tree

        st.success("Prompt generated successfully!")
        st.text_area("Generated Prompt", value=final_prompt, height=500)
        log_placeholder.text("\n".join(log_messages))

    if st.checkbox("Show file tree preview") and st.session_state.get("file_tree"):
        with st.expander("File Tree Preview"):
            for rel_path in st.session_state["file_tree"]:
                st.write(rel_path)


if __name__ == "__main__":
    main()
