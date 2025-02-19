"""Streamlit app for Code2Prompt.

This module provides a web-based interface using Streamlit to transform a ZIP file
containing a codebase into a structured, prompt-optimized format for language models.
Users can select directories to ignore, choose an output format (Plaintext, Markdown, or XML),
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
from typing import List, Set, Tuple, Dict, Any

# Third-party imports
import streamlit as st

# Local application/library-specific imports
from config import DEFAULT_IGNORE_DIRS
from exceptions import FileProcessingError, FormatError, TempFileError
from file_processor import extract_zip, get_files_from_directory


def handle_file_upload() -> str:
    """Handle file upload and save to a temporary location.

    Returns:
        str: Path to the temporary file.
    """
    uploaded_file = st.file_uploader("📁 Upload a ZIP file", type="zip")
    if not uploaded_file:
        return ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            st.info(f"File **{uploaded_file.name}** uploaded successfully!")
            return tmp_file.name
    except (IOError, OSError) as e:
        st.error(f"Failed to save uploaded file: {e}")
        return ""


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
        Tuple[List[str], List[str]]: A tuple containing the list of formatted file contents
        (prompt lines) and the file tree (list of relative paths).
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


@st.cache_data(show_spinner=False)
def process_zip_file(
    temp_zip_path: str,
    ignore_options: Set[str],
    output_format: str,
    options: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """Process the ZIP file and generate the formatted prompt text and file tree preview.

    Args:
        temp_zip_path (str): Path to the temporary ZIP file.
        ignore_options (Set[str]): Set of directories/files to ignore.
        output_format (str): Desired output format.
        options (Dict[str, Any]): Additional formatting options.

    Returns:
        Tuple[str, List[str]]: The generated prompt text and the file tree (list of relative paths).
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
        file_paths = get_files_from_directory(temp_dir, ignore_options)
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
        "Upload a ZIP file and customize your settings for the best results."
    )

    # Initialize session state for prompt and file tree preview.
    if "prompt_text" not in st.session_state:
        st.session_state["prompt_text"] = ""
    if "file_tree" not in st.session_state:
        st.session_state["file_tree"] = []

    # Sidebar settings
    with st.sidebar:
        st.header("Settings")
        ignore_options = st.multiselect(
            "Select directories/files to ignore:",
            options=DEFAULT_IGNORE_DIRS,
            default=DEFAULT_IGNORE_DIRS,
        )
        output_format = st.selectbox(
            "Select Output Format:", options=["Plaintext", "Markdown", "XML"]
        )
        custom_prompt_header = st.text_input(
            "Custom Prompt Header",
            value="",
            help="Optional custom header to include at the top of the generated prompt.",
        )
        include_boundaries = st.checkbox(
            "Include file boundaries",
            value=True,
            help="Include headers/footers for each file.",
        )
        truncate_length = st.number_input(
            "Truncate file content (max characters)",
            min_value=0,
            value=0,
            step=100,
            help="Set to 0 for no truncation.",
        )
        include_metadata = st.checkbox(
            "Include file metadata",
            value=False,
            help="Include file size metadata in the prompt.",
        )
        generate_button = st.button("🔄 Generate Prompt")

    # Handle file upload
    temp_zip_path = handle_file_upload()

    if temp_zip_path and generate_button:
        options = {
            "include_boundaries": include_boundaries,
            "truncate_length": truncate_length,
            "file_metadata": {"size": None} if include_metadata else None,
        }
        try:
            with st.spinner("Processing ZIP file..."):
                prompt_text, file_tree = process_zip_file(
                    temp_zip_path, set(ignore_options), output_format, options
                )
            # Prepend custom header if provided.
            if custom_prompt_header.strip():
                st.session_state["prompt_text"] = (
                    custom_prompt_header.strip() + "\n" + prompt_text
                )
            else:
                st.session_state["prompt_text"] = prompt_text
            st.session_state["file_tree"] = file_tree
            st.success("Prompt generated successfully!")
            st.text_area(
                "Generated Prompt", value=st.session_state["prompt_text"], height=500
            )
        except (FileProcessingError, TempFileError, FormatError) as e:
            st.error(str(e))
        except (ValueError, IOError) as e:
            st.error(f"Error processing data: {e}")
            st.exception(e)
        finally:
            try:
                Path(temp_zip_path).unlink(missing_ok=True)
            except OSError as e:
                st.warning(f"Failed to remove temporary file {temp_zip_path}: {e}")

    # Display file tree preview if requested, using session state
    # (so it doesn't require reprocessing)
    if st.checkbox("Show file tree preview") and st.session_state["file_tree"]:
        with st.expander("File Tree Preview"):
            for rel_path in st.session_state["file_tree"]:
                st.write(rel_path)


if __name__ == "__main__":
    main()
