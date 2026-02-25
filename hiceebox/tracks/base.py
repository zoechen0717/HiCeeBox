"""Abstract base class for genomic tracks."""

from abc import ABC, abstractmethod
from typing import Tuple, Optional
import matplotlib.pyplot as plt


class Track(ABC):
    """
    Abstract base class for all genomic track types.
    
    All track implementations must inherit from this class and implement
    the draw() method.
    """
    
    def __init__(
        self, 
        name: Optional[str] = None, 
        height: float = 1.0, 
        scale: float = 1.0,
        pad_top: float = 0.05, 
        pad_bottom: float = 0.05
    ):
        """
        Initialize a track.
        
        Args:
            name: Display name for the track
            height: Relative height weight for layout (default: 1.0)
            scale: Multiplier for height (default: 1.0). Effective height = height * scale.
            pad_top: Top padding as fraction of track height
            pad_bottom: Bottom padding as fraction of track height
        """
        self.name = name
        self.height = height
        self.scale = scale
        self.pad_top = pad_top
        self.pad_bottom = pad_bottom
    
    @abstractmethod
    def draw(self, ax: plt.Axes, region: Tuple[str, int, int]) -> None:
        """
        Draw the track on the given axes for the specified genomic region.
        
        Args:
            ax: Matplotlib Axes object to draw on
            region: Tuple of (chromosome, start, end)
        """
        pass
    
    def set_xlim(self, ax: plt.Axes, start: int, end: int) -> None:
        """
        Set x-axis limits to match genomic coordinates.
        
        Args:
            ax: Matplotlib Axes object
            start: Start position
            end: End position
        """
        ax.set_xlim(start, end)
    
    def format_axis(self, ax: plt.Axes, show_xlabel: bool = False) -> None:
        """
        Apply standard axis formatting.
        
        Args:
            ax: Matplotlib Axes object
            show_xlabel: Whether to show x-axis label
        """
        if self.name:
            ax.set_ylabel(self.name, rotation=0, ha='right', va='center')
        
        if not show_xlabel:
            ax.set_xlabel('')
            ax.tick_params(labelbottom=False)
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

