"""Main entry point for the Code2Prompt application.

This module initializes the Tkinter application and starts the main loop.
"""

from tkinter import Tk
from gui import CodebasePromptGeneratorGUI


def main() -> None:
    """Initialize and run the Code2Prompt application."""
    root = Tk()
    app = CodebasePromptGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
