"""GenomeView: Main controller for multi-track genomic visualization."""

from typing import Optional, List
from pathlib import Path
import matplotlib.pyplot as plt

from hiceebox.tracks.base import Track
from hiceebox.view.layout import LayoutManager


class GenomeView:
    """
    Main controller for creating multi-track genomic visualizations.
    
    Manages the genomic region, track list, figure layout, and export.
    """
    
    def __init__(
        self,
        chrom: str,
        start: int,
        end: int,
        width: float = 8.0,
        dpi: int = 300,
        title: Optional[str] = None
    ):
        """
        Initialize GenomeView.
        
        Args:
            chrom: Chromosome name (e.g., 'chr6')
            start: Start position in base pairs
            end: End position in base pairs
            width: Figure width in inches
            dpi: Resolution in dots per inch
            title: Optional figure title
        """
        self.chrom = chrom
        self.start = start
        self.end = end
        self.width = width
        self.dpi = dpi
        self.title = title
        
        self.tracks: List[Track] = []
        self._fig = None
        self._axes = None
    
    @property
    def region(self) -> tuple[str, int, int]:
        """Get genomic region as tuple."""
        return (self.chrom, self.start, self.end)
    
    @property
    def region_size(self) -> int:
        """Get region size in base pairs."""
        return self.end - self.start
    
    def add_track(self, track: Track) -> None:
        """
        Add a track to the view.
        
        Args:
            track: Track instance to add
        """
        self.tracks.append(track)
    
    def plot(
        self, 
        output: Optional[str] = None, 
        show: bool = False,
        close: bool = True
    ) -> Optional[plt.Figure]:
        """
        Generate the multi-track plot.
        
        Args:
            output: Output file path (PDF, PNG, or SVG)
            show: Whether to display the plot interactively
            close: Whether to close the figure after saving
            
        Returns:
            Figure object if not closed, None otherwise
        """
        if not self.tracks:
            raise ValueError("No tracks added to GenomeView")
        
        # Create layout
        layout_manager = LayoutManager(
            tracks=self.tracks,
            width=self.width,
            dpi=self.dpi
        )
        
        self._fig, self._axes = layout_manager.create_layout()
        
        # Add title if specified
        if self.title:
            self._fig.suptitle(self.title, fontsize=12, y=0.98)
        
        # Draw each track
        for track, ax in zip(self.tracks, self._axes):
            track.draw(ax, self.region)
        
        # Add genomic position label to bottom track
        if self._axes:
            bottom_ax = self._axes[-1]
            bottom_ax.set_xlabel(
                f"{self.chrom}:{self.start:,}-{self.end:,} ({self.region_size:,} bp)",
                fontsize=10
            )
            bottom_ax.tick_params(labelbottom=True)
        
        # Adjust layout
        self._fig.tight_layout()
        
        # Save if output path specified
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Determine format from extension
            suffix = output_path.suffix.lower()
            if suffix == '.pdf':
                self._fig.savefig(output, format='pdf', dpi=self.dpi, bbox_inches='tight')
            elif suffix == '.png':
                self._fig.savefig(output, format='png', dpi=self.dpi, bbox_inches='tight')
            elif suffix == '.svg':
                self._fig.savefig(output, format='svg', dpi=self.dpi, bbox_inches='tight')
            else:
                raise ValueError(f"Unsupported output format: {suffix}")
            
            print(f"Saved figure to: {output}")
        
        # Show if requested
        if show:
            plt.show()
        
        # Close or return figure
        if close and not show:
            plt.close(self._fig)
            return None
        else:
            return self._fig
    
    def clear_tracks(self) -> None:
        """Remove all tracks from the view."""
        self.tracks.clear()
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"GenomeView({self.chrom}:{self.start}-{self.end}, "
            f"{len(self.tracks)} tracks)"
        )

