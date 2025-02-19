"""Streamlit app for Code2Prompt.

This module provides a web-based interface using Streamlit to transform a ZIP file
containing a codebase into a structured, prompt-optimized format for language models.
Users can select directories to ignore and choose an output format (Plaintext, Markdown, or XML).

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
from typing import List, Optional, Set

# Third-party imports
import streamlit as st

# Local application/library-specific imports
from config import DEFAULT_IGNORE_DIRS
from exceptions import FileProcessingError, FormatError, TempFileError
from file_processor import extract_zip, get_files_from_directory


def handle_file_upload() -> Optional[str]:
    """Handle file upload and save to temporary location.

    Returns:
        Optional[str]: Path to temporary file if successful, None otherwise
    """
    uploaded_file = st.file_uploader("📁 Upload a ZIP file", type="zip")
    if not uploaded_file:
        return None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            st.info(f"File **{uploaded_file.name}** uploaded successfully!")
            return tmp_file.name
    except (IOError, OSError) as e:
        st.error(f"Failed to save uploaded file: {e}")
        return None


def process_files(
    file_paths: List[str], temp_dir: str, output_format: str
) -> List[str]:
    """Process individual files and format their content.

    Args:
        file_paths (List[str]): List of file paths to process
        temp_dir (str): Temporary directory containing the files
        output_format (str): Desired output format

    Returns:
        List[str]: List of formatted file contents
    """
    prompt_lines = [
        "Below is the structured project codebase extracted from the provided ZIP file:\n"
    ]

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

        try:
            rel_path = os.path.relpath(file_path, temp_dir)
            formatted = format_file_content(rel_path, content, output_format)
            prompt_lines.append(formatted)
        except Exception as e:
            raise FormatError(f"Failed to format {rel_path}: {e}") from e

    return prompt_lines


@st.cache_data(show_spinner=False)
def process_zip_file(
    temp_zip_path: str, ignore_options: Set[str], output_format: str
) -> str:
    """Process the ZIP file and generate the formatted prompt text.

    Args:
        temp_zip_path (str): Path to the temporary ZIP file
        ignore_options (Set[str]): Set of directories/files to ignore
        output_format (str): Desired output format

    Returns:
        str: The generated prompt text
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
        prompt_lines = process_files(file_paths, temp_dir, output_format)
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except OSError as e:
            st.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")

    return "\n".join(prompt_lines)


def show_file_tree_preview(temp_zip_path: str, ignore_options: Set[str]) -> None:
    """Display a preview of the file tree.

    Args:
        temp_zip_path (str): Path to the temporary ZIP file
        ignore_options (Set[str]): Set of directories/files to ignore
    """
    try:
        temp_dir = extract_zip(temp_zip_path)
        try:
            file_paths = get_files_from_directory(temp_dir, ignore_options)
            for file_path in file_paths:
                rel_path = os.path.relpath(file_path, temp_dir)
                st.write(rel_path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except (zipfile.BadZipFile, OSError) as e:
        st.error(f"Failed to generate file tree preview: {e}")


def main() -> None:
    """Main function to run the Code2Prompt Streamlit app."""
    st.set_page_config(page_title="Code2Prompt 🚀", layout="wide")
    st.title("Code2Prompt 🚀")
    st.markdown(
        "Transform your codebase into a structured, prompt-optimized format for LLMs like ChatGPT. "
        "Upload a ZIP file and customize your settings for the best results."
    )

    # Handle settings in sidebar
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
        generate_button = st.button("🔄 Generate Prompt")

    # Handle file upload
    temp_zip_path = handle_file_upload()

    if temp_zip_path and generate_button:
        try:
            with st.spinner("Processing ZIP file..."):
                prompt_text = process_zip_file(
                    temp_zip_path, set(ignore_options), output_format
                )
            st.success("Prompt generated successfully!")
            st.text_area("Generated Prompt", value=prompt_text, height=500)

            if st.checkbox("Show file tree preview"):
                with st.expander("File Tree Preview"):
                    show_file_tree_preview(temp_zip_path, set(ignore_options))

        except (FileProcessingError, TempFileError, FormatError) as e:
            st.error(str(e))
        except (ValueError, IOError) as e:
            st.error(f"Error processing data: {e}")
            st.exception(e)
        finally:
            if temp_zip_path:
                try:
                    Path(temp_zip_path).unlink(missing_ok=True)
                except OSError as e:
                    st.warning(f"Failed to remove temporary file {temp_zip_path}: {e}")


if __name__ == "__main__":
    main()
