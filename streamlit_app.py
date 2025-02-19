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
from typing import List, Set

# Third-party imports
import streamlit as st

# Local project-specific imports (custom modules)
from config import DEFAULT_IGNORE_DIRS
from file_processor import extract_zip, get_files_from_directory

# pylint: disable=deprecated-module
from formatter import format_file_content


@st.cache_data(show_spinner=False)
def process_zip_file(
    temp_zip_path: str, ignore_options: Set[str], output_format: str
) -> str:
    """Process the ZIP file and generate the formatted prompt text.

    Args:
        temp_zip_path (str): Path to the temporary ZIP file.
        ignore_options (Set[str]): Set of directories/files to ignore.
        output_format (str): Desired output format.

    Returns:
        str: The generated prompt text.
    """
    temp_dir: str = extract_zip(temp_zip_path)
    file_paths: List[str] = get_files_from_directory(temp_dir, ignore_options)
    prompt_lines: List[str] = [
        "Below is the structured project codebase extracted from the provided ZIP file:\n"
    ]
    for file_path in file_paths:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content: str = f.read()
        except (UnicodeDecodeError, IOError, PermissionError) as e:
            # Skip files that cannot be read due to encoding, permissions, or I/O issues
            st.warning(f"Failed to read file: {file_path} ({e})")
            continue
        rel_path: str = os.path.relpath(file_path, temp_dir)
        formatted: str = format_file_content(rel_path, content, output_format)
        prompt_lines.append(formatted)
    shutil.rmtree(temp_dir, ignore_errors=True)
    return "\n".join(prompt_lines)


def main() -> None:
    """Main function to run the Code2Prompt Streamlit app."""
    st.set_page_config(page_title="Code2Prompt 🚀", layout="wide")
    st.title("Code2Prompt 🚀")
    st.markdown(
        "Transform your codebase into a structured, prompt-optimized format for LLMs like ChatGPT. "
        "Upload a ZIP file and customize your settings for the best results."
    )

    # File uploader for ZIP files.
    uploaded_file = st.file_uploader("📁 Upload a ZIP file", type="zip")

    # Sidebar for settings.
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

    if uploaded_file is not None:
        # Save the uploaded file to a temporary location.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            temp_zip_path: str = tmp_file.name

        st.info(f"File **{uploaded_file.name}** uploaded successfully!")

        if generate_button:
            with st.spinner("Processing ZIP file..."):
                prompt_text: str = process_zip_file(
                    temp_zip_path, set(ignore_options), output_format
                )
            st.success("Prompt generated successfully!")
            st.text_area("Generated Prompt", value=prompt_text, height=500)

            # Optional: Provide a file tree preview if desired.
            if st.checkbox("Show file tree preview"):
                with st.expander("File Tree Preview"):
                    temp_dir = extract_zip(temp_zip_path)
                    file_paths: List[str] = get_files_from_directory(
                        temp_dir, set(ignore_options)
                    )
                    for file_path in file_paths:
                        rel_path: str = os.path.relpath(file_path, temp_dir)
                        st.write(rel_path)
                    shutil.rmtree(temp_dir, ignore_errors=True)

            os.remove(temp_zip_path)


if __name__ == "__main__":
    main()
