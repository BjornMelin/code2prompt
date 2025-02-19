"""Module for the GUI of the Code2Prompt application.

This module creates a Tkinter-based graphical user interface for loading ZIP files,
configuring ignore settings, selecting output formats, generating optimized prompts,
and copying the generated prompt to the clipboard.
"""

import os
import shutil
from tkinter import Tk, Toplevel, Frame, Button, Label, BooleanVar, StringVar
from tkinter import filedialog, messagebox, scrolledtext
from tkinter.ttk import Combobox, Style
from typing import Set
import tkinter as tk
from pathlib import Path
from tkinterdnd2 import DND_FILES, TkinterDnD

from config import DEFAULT_IGNORE_DIRS
from file_processor import extract_zip, get_files_from_directory
from formatter import format_file_content

class DragDropFrame(Frame):
    """A frame that supports drag and drop file uploads."""
    
    def __init__(self, master, callback):
        super().__init__(master, bg='#f0f0f0', height=100, width=400)
        self.callback = callback
        self.pack_propagate(False)
        
        self.drop_label = Label(
            self,
            text="Drag & Drop ZIP file here\nor click to browse",
            bg='#f0f0f0',
            fg='#666666',
            font=('Arial', 12)
        )
        self.drop_label.pack(expand=True)
        
        # Bind events
        self.drop_label.bind('<Button-1>', self.on_click)
        self.bind('<Drop>', self.on_drop)
        self.bind('<Enter>', self.on_drag_enter)
        self.bind('<Leave>', self.on_drag_leave)
        
        # Enable drop target
        self.drop_target_register(DND_FILES)
        
    def on_drag_enter(self, event):
        self.configure(bg='#e0e0e0')
        self.drop_label.configure(bg='#e0e0e0')
        
    def on_drag_leave(self, event):
        self.configure(bg='#f0f0f0')
        self.drop_label.configure(bg='#f0f0f0')
        
    def on_drop(self, event):
        file_path = event.data
        if file_path.lower().endswith('.zip'):
            self.callback(file_path)
        else:
            messagebox.showerror("Error", "Please select a ZIP file")
            
    def on_click(self, event):
        file_path = filedialog.askopenfilename(
            title="Select ZIP File",
            filetypes=[("ZIP Files", "*.zip")]
        )
        if file_path:
            self.callback(file_path)


class CodebasePromptGeneratorGUI:
    """Class representing the main GUI for the Code2Prompt application."""

    def __init__(self, master: TkinterDnD.Tk) -> None:
        """Initialize the GUI and its components.

        Args:
            master (TkinterDnD.Tk): The root Tkinter window.
        """
        self.master: TkinterDnD.Tk = master
        self.master.title("Code2Prompt 🚀")
        
        # Configure modern style
        self.style = Style()
        self.style.configure('Modern.TButton',
                           padding=10,
                           font=('Arial', 10))
        self.style.configure('Modern.TCombobox',
                           padding=5,
                           font=('Arial', 10))
        
        # Initialize ignore options with defaults
        self.ignore_options = {
            name: BooleanVar(value=True) for name in DEFAULT_IGNORE_DIRS
        }

        # Main container with padding
        main_container = Frame(self.master, padx=20, pady=20)
        main_container.pack(fill="both", expand=True)

        # File upload section with drag & drop
        upload_frame = Frame(main_container)
        upload_frame.pack(fill="x", pady=(0, 20))
        
        self.drag_drop = DragDropFrame(upload_frame, self.on_file_selected)
        self.drag_drop.pack(fill="x", pady=(0, 10))
        
        # Status label
        self.status_label = Label(
            upload_frame,
            text="No file selected",
            font=('Arial', 10),
            fg='#666666'
        )
        self.status_label.pack(fill="x")

        # Controls frame
        controls_frame = Frame(main_container)
        controls_frame.pack(fill="x", pady=(0, 10))

        # Left side controls
        left_controls = Frame(controls_frame)
        left_controls.pack(side="left")

        self.ignore_button = Button(
            left_controls,
            text="📁 Ignore Settings",
            command=self.open_ignore_window,
            style='Modern.TButton'
        )
        self.ignore_button.pack(side="left", padx=(0, 10))

        format_frame = Frame(left_controls)
        format_frame.pack(side="left")
        
        Label(format_frame,
              text="Output Format:",
              font=('Arial', 10)).pack(side="left", padx=(0, 5))
              
        self.format_var = StringVar(master=self.master, value="Plaintext")
        self.format_combo = Combobox(
            format_frame,
            textvariable=self.format_var,
            values=["Plaintext", "Markdown", "XML"],
            state="readonly",
            width=12,
            style='Modern.TCombobox'
        )
        self.format_combo.pack(side="left")

        # Right side controls
        right_controls = Frame(controls_frame)
        right_controls.pack(side="right")

        self.generate_button = Button(
            right_controls,
            text="🔄 Generate Prompt",
            command=self.generate_prompt,
            state="disabled",
            style='Modern.TButton'
        )
        self.generate_button.pack(side="left", padx=(0, 10))

        self.copy_button = Button(
            right_controls,
            text="📋 Copy to Clipboard",
            command=self.copy_to_clipboard,
            state="disabled",
            style='Modern.TButton'
        )
        self.copy_button.pack(side="left")

        # Text area with modern styling
        self.text_area = scrolledtext.ScrolledText(
            main_container,
            wrap="word",
            width=100,
            height=30,
            font=('Arial', 11),
            bg='#ffffff',
            fg='#333333'
        )
        self.text_area.pack(fill="both", expand=True)

        self.zip_path: str = ""
        self.prompt_text: str = ""

    def on_file_selected(self, file_path: str) -> None:
        """Handle file selection from drag-drop or click events.
        
        Args:
            file_path (str): Path to the selected ZIP file
        """
        self.zip_path = file_path
        self.generate_button.config(state="normal")
        self.status_label.config(
            text=f"Selected: {Path(file_path).name}",
            fg='#28a745'
        )
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
