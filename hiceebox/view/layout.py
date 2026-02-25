"""Layout manager for multi-track figures."""

from typing import List, Tuple
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from hiceebox.tracks.base import Track


class LayoutManager:
    """
    Manages vertical layout of multiple tracks using GridSpec.
    
    Converts track height weights to actual figure dimensions and creates
    properly spaced matplotlib axes.
    """
    
    def __init__(
        self,
        tracks: List[Track],
        width: float = 8.0,
        dpi: int = 300,
        hspace: float = 0.3
    ):
        """
        Initialize layout manager.
        
        Args:
            tracks: List of Track objects to layout
            width: Figure width in inches
            dpi: Resolution in dots per inch
            hspace: Vertical spacing between tracks (in inches)
        """
        self.tracks = tracks
        self.width = width
        self.dpi = dpi
        self.hspace = hspace
    
    def _calculate_heights(self) -> Tuple[List[float], float]:
        """
        Calculate individual track heights and total figure height.
        
        Returns:
            tuple: (height_ratios, total_height)
                - height_ratios: List of relative height weights for GridSpec
                - total_height: Total figure height in inches
        """
        # Get height weights
        height_ratios = []
        total_weight = 0.0
        
        for track in self.tracks:
            # Account for padding and scale (height * scale)
            scale = getattr(track, 'scale', 1.0)
            effective_height = track.height * scale * (1.0 + track.pad_top + track.pad_bottom)
            height_ratios.append(effective_height)
            total_weight += effective_height
        
        # Calculate total figure height
        # Use a reasonable scaling factor
        base_height_per_unit = 2.0  # inches per unit weight
        total_height = total_weight * base_height_per_unit
        
        # Add space for gaps
        gap_space = self.hspace * (len(self.tracks) - 1)
        total_height += gap_space
        
        return height_ratios, total_height
    
    def create_layout(self) -> Tuple[plt.Figure, List[plt.Axes]]:
        """
        Create figure and axes layout for all tracks.
        
        Returns:
            tuple: (figure, axes_list)
                - figure: Matplotlib Figure object
                - axes_list: List of Axes objects, one per track
        """
        if not self.tracks:
            raise ValueError("No tracks provided for layout")
        
        # Calculate heights
        height_ratios, total_height = self._calculate_heights()
        
        # Create figure
        fig = plt.figure(figsize=(self.width, total_height), dpi=self.dpi)
        
        # Create GridSpec
        gs = gridspec.GridSpec(
            nrows=len(self.tracks),
            ncols=1,
            figure=fig,
            height_ratios=height_ratios,
            hspace=0.1  # Relative spacing
        )
        
        # Create axes
        axes = []
        for i in range(len(self.tracks)):
            ax = fig.add_subplot(gs[i])
            axes.append(ax)
        
        return fig, axes
    
    def __repr__(self) -> str:
        """String representation."""
        return f"LayoutManager({len(self.tracks)} tracks, {self.width}x{self._calculate_heights()[1]:.1f} in)"

