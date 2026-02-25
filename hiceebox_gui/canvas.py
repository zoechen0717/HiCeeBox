"""
Matplotlib canvas widget for HiCeeBox GUI.

Wraps matplotlib's FigureCanvas for Qt integration.
"""

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QSizePolicy


class GenomeCanvas(FigureCanvas):
    """
    Qt-compatible matplotlib canvas for displaying genomic tracks.
    
    This widget embeds matplotlib figures in the Qt application.
    """
    
    def __init__(self, parent=None, width=12, height=8, dpi=100):
        """
        Initialize canvas with a matplotlib figure.
        
        Args:
            parent: Parent Qt widget
            width: Figure width in inches
            height: Figure height in inches
            dpi: Figure resolution
        """
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        
        super().__init__(self.fig)
        
        self.setParent(parent)
        
        # Set size policy to expand
        FigureCanvas.setSizePolicy(
            self,
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        FigureCanvas.updateGeometry(self)
    
    def get_figure(self) -> Figure:
        """
        Get the underlying matplotlib figure.
        
        Returns:
            Matplotlib Figure object
        """
        return self.fig
    
    def clear(self) -> None:
        """Clear the figure."""
        self.fig.clear()
        self.draw()
    
    def refresh(self) -> None:
        """Refresh the canvas display."""
        self.draw()

