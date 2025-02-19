"""Streamlit app for Code2Prompt.

This module provides a web-based interface using Streamlit to transform one or more ZIP files
containing codebases into structured, prompt-optimized formats for language models.
Users can select directories to ignore, filter file types, choose an output format,
and customize various aspects of the generated prompt.

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
from config import DEFAULT_FILE_TYPES, DEFAULT_IGNORE_DIRS
from exceptions import FileProcessingError, FormatError, TempFileError
from file_processor import extract_zip, get_files_from_directory


def inject_custom_css(theme: str) -> None:
    """Inject custom CSS for theme styling.

    Args:
        theme (str): 'light' or 'dark'
    """
    theme_css = {
        "dark": """
            body { background-color: #2E2E2E; color: #FFFFFF; }
            .css-1d391kg, .css-1d391kg * { background-color: #3E3E3E; }
        """,
        "light": """
            body { background-color: #FFFFFF; color: #000000; }
        """,
    }
    css = f"<style>{theme_css[theme]}</style>"
    st.markdown(css, unsafe_allow_html=True)


def handle_file_upload(multi: bool = True) -> List[str]:
    """Handle file upload and save to temporary location.

    Args:
        multi (bool): If True, allow multiple files.

    Returns:
        List[str]: List of temporary file paths.
    """
    uploaded_files = st.file_uploader(
        "📁 Upload ZIP file(s)", type="zip", accept_multiple_files=multi
    )
    temp_paths = []
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
        output_format (str): Desired output format.
        options (Dict[str, Any]): Formatting options to pass to formatter.

    Returns:
        Tuple[List[str], List[str]]: Formatted prompt lines and file tree (list of relative paths).
    """
    prompt_lines = [
        "Below is the structured project codebase extracted from the provided ZIP file:\n"
    ]
    file_tree = []

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

        rel_path = os.path.relpath(file_path, temp_dir)
        file_tree.append(rel_path)
        try:
            formatted = format_file_content(rel_path, content, output_format, options)
            prompt_lines.append(formatted)
        except Exception as e:
            raise FormatError(f"Failed to format {rel_path}: {e}") from e

    return prompt_lines, file_tree


def setup_sidebar_options() -> Tuple[Set[str], str, dict, Set[str]]:
    """Setup and get all sidebar options.

    Returns:
        Tuple containing ignore options, output format, formatting options, and file types.
    """
    st.sidebar.header("Settings")

    # Ignore options
    ignore_options = set(
        st.sidebar.multiselect(
            "Select directories/files to ignore:",
            options=DEFAULT_IGNORE_DIRS,
            default=DEFAULT_IGNORE_DIRS,
        )
    )

    custom_ignore = st.sidebar.text_input(
        "Add custom ignore pattern (comma-separated):",
        value="",
        help="Enter additional directories/files to ignore, separated by commas.",
    )
    if custom_ignore:
        custom_list = {x.strip() for x in custom_ignore.split(",") if x.strip()}
        ignore_options.update(custom_list)

    # Output format and options
    output_format = st.sidebar.selectbox(
        "Select Output Format:", options=["Plaintext", "Markdown", "XML"]
    )

    format_options = {
        "include_boundaries": st.sidebar.checkbox(
            "Include file boundaries",
            value=True,
            help="Include headers/footers for each file.",
        ),
        "truncate_length": st.sidebar.number_input(
            "Truncate file content (max characters):",
            min_value=0,
            value=0,
            step=100,
            help="Set to 0 for no truncation.",
        ),
        "file_metadata": (
            {"size": None}
            if st.sidebar.checkbox(
                "Include file metadata",
                value=False,
                help="Include file size metadata in the prompt.",
            )
            else None
        ),
    }

    # File types
    file_types = set(
        ft.lower()
        for ft in st.sidebar.multiselect(
            "Filter by file types (extensions):",
            options=DEFAULT_FILE_TYPES,
            default=DEFAULT_FILE_TYPES,
            help="Select the file types you want to process.",
        )
    )

    return ignore_options, output_format, format_options, file_types


def process_uploads(
    temp_zip_paths: List[str],
    ignore_options: Set[str],
    output_format: str,
    format_options: Dict[str, Any],
    file_types: Set[str],
) -> Tuple[str, List[str], List[str]]:
    """Process uploaded ZIP files and generate prompt text.

    Args:
        temp_zip_paths: List of temporary ZIP file paths
        ignore_options: Set of directories/files to ignore
        output_format: Desired output format
        format_options: Formatting options
        file_types: Set of file extensions to include

    Returns:
        Tuple of final prompt text, file tree list, and log messages
    """
    all_prompt_texts = []
    all_file_trees = []
    log_messages = []

    progress_bar = st.progress(0)
    total_files = len(temp_zip_paths)

    for idx, temp_zip_path in enumerate(temp_zip_paths):
        try:
            with st.spinner(f"Processing file {idx+1} of {total_files}..."):
                prompt_text, file_tree = process_zip_file(
                    temp_zip_path,
                    ignore_options,
                    output_format,
                    format_options,
                    file_types,
                )
            all_prompt_texts.append(prompt_text)
            all_file_trees.extend(file_tree)
            log_messages.append(f"Processed {Path(temp_zip_path).name} successfully.")
        except (FileProcessingError, FormatError, TempFileError, IOError, OSError) as e:
            log_messages.append(f"Error processing {Path(temp_zip_path).name}: {e}")
        finally:
            try:
                Path(temp_zip_path).unlink(missing_ok=True)
            except OSError as e:
                log_messages.append(
                    f"Failed to remove temporary file {temp_zip_path}: {e}"
                )
        progress_bar.progress((idx + 1) / total_files)

    return "\n".join(all_prompt_texts), all_file_trees, log_messages


@st.cache_data(show_spinner=False)
def process_zip_file(
    temp_zip_path: str,
    ignore_options: Set[str],
    output_format: str,
    options: Dict[str, Any],
    file_types: Set[str],
) -> Tuple[str, List[str]]:
    """Process the ZIP file and generate the formatted prompt text and file tree preview.

    Args:
        temp_zip_path (str): Path to the temporary ZIP file.
        ignore_options (Set[str]): Set of directories/files to ignore.
        output_format (str): Desired output format.
        options (Dict[str, Any]): Additional formatting options.
        file_types (Set[str]): Set of file extensions to include.

    Returns:
        Tuple[str, List[str]]: Generated prompt text and file tree (list of relative paths).
    """
    try:
        temp_dir = extract_zip(temp_zip_path)
    except zipfile.BadZipFile as e:
        raise FileProcessingError(f"Invalid or corrupted ZIP file: {e}") from e
    except OSError as e:
        raise TempFileError(
            f"Failed to create or access temporary directory: {e}"
        ) from e

    try:
        file_paths = get_files_from_directory(temp_dir, ignore_options, file_types)
        prompt_lines, file_tree = process_files(
            file_paths, temp_dir, output_format, options
        )
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except OSError as e:
            st.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")

    return "\n".join(prompt_lines), file_tree


def main() -> None:
    """Main function to run the Code2Prompt Streamlit app."""
    st.set_page_config(page_title="Code2Prompt 🚀", layout="wide")
    st.title("Code2Prompt 🚀")
    st.markdown(
        "Transform your codebase into a structured, prompt-optimized format for LLMs like ChatGPT. "
        "Upload ZIP file(s) and customize your settings for optimal results."
    )

    # Theme toggle
    theme = st.sidebar.selectbox("Select Theme:", options=["Light", "Dark"], index=0)
    inject_custom_css(theme.lower())

    # Get sidebar options
    ignore_options, output_format, format_options, file_types = setup_sidebar_options()
    generate_button = st.sidebar.button("🔄 Generate Prompt")

    # Process file uploads
    temp_zip_paths = handle_file_upload(multi=True)
    log_placeholder = st.empty()

    if temp_zip_paths and generate_button:
        # Process uploads and generate prompt
        prompt_text, file_tree, log_messages = process_uploads(
            temp_zip_paths, ignore_options, output_format, format_options, file_types
        )

        # Add custom header if provided
        custom_header = st.sidebar.text_input(
            "Custom Prompt Header:",
            value="",
            help="Optional custom header to include at the top of the generated prompt.",
        )
        final_prompt = (
            f"{custom_header.strip()}\n" if custom_header.strip() else ""
        ) + prompt_text

        # Store results in session state
        st.session_state["prompt_text"] = final_prompt
        st.session_state["file_tree"] = file_tree

        # Display results
        st.success("Prompt generated successfully!")
        st.text_area("Generated Prompt", value=final_prompt, height=500)
        log_placeholder.text("\n".join(log_messages))

    # Display file tree preview if requested
    if st.checkbox("Show file tree preview") and st.session_state.get("file_tree"):
        with st.expander("File Tree Preview"):
            for rel_path in st.session_state["file_tree"]:
                st.write(rel_path)


if __name__ == "__main__":
    main()
