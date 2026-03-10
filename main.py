#!/usr/bin/env python3
"""
PersonaLive Client - Entry point
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from gui.main_window import MainWindow


def main():
    """Application entry point."""
    # Enable High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("PersonaLive Client")
    app.setApplicationVersion("1.0.0")
    
    # Set global font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()