"""Main entry point for the Code2Prompt application.

This module initializes the Tkinter application with drag-and-drop support and starts the main loop.
"""

from tkinterdnd2 import TkinterDnD
from gui import CodebasePromptGeneratorGUI


def main() -> None:
    """Initialize and run the Code2Prompt application."""
    root = TkinterDnD.Tk()
    root.configure(bg='#f5f5f5')  # Set a modern background color
    root.geometry('1000x800')     # Set a reasonable default window size
    app = CodebasePromptGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
