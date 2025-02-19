"""Module for the GUI of the Code2Prompt application.

This module creates a Tkinter-based graphical user interface for loading ZIP files,
configuring ignore settings, selecting output formats, generating optimized prompts,
and copying the generated prompt to the clipboard.
"""

import os
import shutil
from tkinter import Tk, Toplevel, Frame, Button, Label, BooleanVar, StringVar
from tkinter import filedialog, messagebox, scrolledtext
from tkinter.ttk import Combobox
from typing import Set

from config import DEFAULT_IGNORE_DIRS
from file_processor import extract_zip, get_files_from_directory
from formatter import format_file_content


class CodebasePromptGeneratorGUI:
    """Class representing the main GUI for the Code2Prompt application."""

    def __init__(self, master: Tk) -> None:
        """Initialize the GUI and its components.

        Args:
            master (Tk): The root Tkinter window.
        """
        self.master: Tk = master
        self.master.title("Code2Prompt 🚀")

        # Initialize ignore options with defaults.
        self.ignore_options = {
            name: BooleanVar(value=True) for name in DEFAULT_IGNORE_DIRS
        }

        # Top frame for file selection and settings.
        top_frame: Frame = Frame(self.master)
        top_frame.pack(pady=5, padx=10, fill="x")

        self.load_button: Button = Button(
            top_frame, text="Load .zip File", command=self.load_zip
        )
        self.load_button.grid(row=0, column=0, padx=5)

        self.ignore_button: Button = Button(
            top_frame, text="Ignore Settings", command=self.open_ignore_window
        )
        self.ignore_button.grid(row=0, column=1, padx=5)

        Label(top_frame, text="Output Format:").grid(row=0, column=2, padx=5)
        self.format_var = StringVar(master=self.master, value="Plaintext")
        self.format_combo: Combobox = Combobox(
            top_frame,
            textvariable=self.format_var,
            values=["Plaintext", "Markdown", "XML"],
            state="readonly",
            width=12,
        )
        self.format_combo.grid(row=0, column=3, padx=5)

        self.generate_button: Button = Button(
            top_frame,
            text="Generate Prompt",
            command=self.generate_prompt,
            state="disabled",
        )
        self.generate_button.grid(row=0, column=4, padx=5)

        self.copy_button: Button = Button(
            top_frame,
            text="Copy to Clipboard",
            command=self.copy_to_clipboard,
            state="disabled",
        )
        self.copy_button.grid(row=0, column=5, padx=5)

        self.text_area = scrolledtext.ScrolledText(
            self.master, wrap="word", width=100, height=30
        )
        self.text_area.pack(padx=10, pady=10)

        self.zip_path: str = ""
        self.prompt_text: str = ""

    def load_zip(self) -> None:
        """Load a ZIP file using a file dialog."""
        self.zip_path = filedialog.askopenfilename(
            title="Select ZIP File", filetypes=[("ZIP Files", "*.zip")]
        )
        if self.zip_path:
            self.generate_button.config(state="normal")
            self.text_area.delete("1.0", "end")
            self.text_area.insert("end", f"Selected file: {self.zip_path}\n")

    def open_ignore_window(self) -> None:
        """Open a window for selecting directories/files to ignore."""
        self.ignore_win = Toplevel(self.master)
        self.ignore_win.title("Select Directories/Files to Ignore")
        row = 0
        for name, var in self.ignore_options.items():
            # Toggle the BooleanVar when the button is clicked.
            Button(
                self.ignore_win,
                text=name,
                command=lambda v=var: v.set(not v.get()),
            ).grid(row=row, column=0, sticky="w", padx=10, pady=2)
            row += 1
        btn_frame = Frame(self.ignore_win)
        btn_frame.grid(row=row, column=0, pady=5)
        Button(btn_frame, text="Select All", command=self.select_all_ignores).pack(
            side="left", padx=5
        )
        Button(btn_frame, text="Unselect All", command=self.unselect_all_ignores).pack(
            side="left", padx=5
        )
        Button(btn_frame, text="OK", command=self.ignore_win.destroy).pack(
            side="left", padx=5
        )

    def select_all_ignores(self) -> None:
        """Select all ignore options."""
        for var in self.ignore_options.values():
            var.set(True)

    def unselect_all_ignores(self) -> None:
        """Unselect all ignore options."""
        for var in self.ignore_options.values():
            var.set(False)

    def generate_prompt(self) -> None:
        """Generate the prompt based on the loaded ZIP file and selected settings."""
        if not self.zip_path:
            messagebox.showerror("Error", "No ZIP file selected!")
            return

        try:
            temp_dir: str = extract_zip(self.zip_path)
        except Exception as e:
            messagebox.showerror("Extraction Error", str(e))
            return

        selected_ignores: Set[str] = {
            name for name, var in self.ignore_options.items() if var.get()
        }
        output_format: str = self.format_var.get()

        prompt_lines: list[str] = []
        prompt_lines.append(
            "Below is the structured project codebase extracted from the provided ZIP file:\n"
        )

        files = get_files_from_directory(temp_dir, selected_ignores)
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            rel_path: str = os.path.relpath(file_path, temp_dir)
            formatted: str = format_file_content(rel_path, content, output_format)
            prompt_lines.append(formatted)

        self.prompt_text = "\n".join(prompt_lines)
        self.text_area.delete("1.0", "end")
        self.text_area.insert("end", self.prompt_text)
        self.copy_button.config(state="normal")

        shutil.rmtree(temp_dir)

    def copy_to_clipboard(self) -> None:
        """Copy the generated prompt text to the clipboard."""
        self.master.clipboard_clear()
        self.master.clipboard_append(self.prompt_text)
        messagebox.showinfo("Copied", "Prompt copied to clipboard!")
