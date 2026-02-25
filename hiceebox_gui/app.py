"""
Entry point for HiCeeBox GUI application.

Initializes Qt application and displays main window.
"""

import sys
import os

# Fix text input in frozen app on macOS: set before any Qt load.
# Empty string = use system (Cocoa) input; "qt" = use Qt's. Try both if one fails.
if getattr(sys, "frozen", False) and sys.platform == "darwin":
    os.environ["QT_IM_MODULE"] = os.environ.get("QT_IM_MODULE", "")

# Force Qt backend for matplotlib before any other imports.
# PyInstaller may otherwise package only MacOSX backend, causing crash when opening the frozen app.
import matplotlib
matplotlib.use("QtAgg")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from hiceebox_gui.main_window import MainWindow


def main():
    """
    Main entry point for HiCeeBox GUI application.
    
    Initializes QApplication and shows the main window.
    """
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("HiCeeBox")
    app.setOrganizationName("HiCeeBox")
    app.setApplicationVersion("0.1.0")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    # Force focus on macOS (helps keyboard input in frozen .app)
    if sys.platform == "darwin":
        window.activateWindow()
        window.raise_()
        # Give focus to Gene input so user can type immediately
        gene_input = getattr(window.nav_bar, "gene_input", None)
        if gene_input is not None:
            QTimer.singleShot(100, lambda: gene_input.setFocus())
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

