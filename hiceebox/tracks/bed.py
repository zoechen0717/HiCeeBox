"""BED track for genomic intervals."""

from typing import Tuple, Optional, List
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from hiceebox.tracks.base import Track


class BedTrack(Track):
    """
    Track for displaying genomic intervals from BED files.
    
    Displays intervals as horizontal bars.
    """
    
    def __init__(
        self,
        filepath: str,
        name: Optional[str] = None,
        color: str = "#8B1538",
        alpha: float = 0.7,
        height: float = 0.5,
        pad_top: float = 0.05,
        pad_bottom: float = 0.05,
        style: str = "box"
    ):
        """
        Initialize BED track.
        
        Args:
            filepath: Path to BED file
            name: Track name (defaults to filename)
            color: Feature color
            alpha: Transparency (0-1)
            height: Relative height weight
            pad_top: Top padding fraction
            pad_bottom: Bottom padding fraction
            style: Display style ('box' or 'highlight')
        """
        track_name = name or Path(filepath).stem
        super().__init__(name=track_name, height=height, pad_top=pad_top, pad_bottom=pad_bottom)
        
        self.filepath = Path(filepath)
        self.color = color
        self.alpha = alpha
        self.style = style
        
        self._intervals = None  # Cached intervals
        
        self._validate_file()
    
    def _validate_file(self) -> None:
        """Validate that the file exists."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"BED file not found: {self.filepath}")
    
    def draw(self, ax: plt.Axes, region: Tuple[str, int, int]) -> None:
        """
        Draw BED intervals as boxes or highlights.
        
        Parses BED file, filters intervals overlapping the region, and renders
        them as rectangles or full-height highlights.
        
        Args:
            ax: Matplotlib Axes to draw on
            region: Genomic region (chrom, start, end)
        """
        chrom, start, end = region
        
        try:
            # Load and filter intervals
            intervals = self._get_filtered_intervals(chrom, start, end)
            
            if len(intervals) == 0:
                # No intervals in region
                ax.text(
                    0.5, 0.5,
                    f"No intervals in region",
                    transform=ax.transAxes,
                    ha='center', va='center',
                    fontsize=9, color='gray'
                )
                ax.set_ylim(0, 1)
            else:
                # Render intervals
                if self.style == 'highlight':
                    self._draw_highlights(ax, intervals)
                else:
                    self._draw_boxes(ax, intervals)
            
        except Exception as e:
            # Handle errors gracefully
            ax.text(
                0.5, 0.5,
                f"Error loading BED:\n{str(e)}",
                transform=ax.transAxes,
                ha='center', va='center',
                fontsize=8, color='red'
            )
            ax.set_ylim(0, 1)
        
        self.set_xlim(ax, start, end)
        self.format_axis(ax, show_xlabel=False)
    
    def _load_bed_file(self) -> List[Tuple[str, int, int]]:
        """
        Load BED file and parse intervals.
        
        Returns:
            List of (chrom, start, end) tuples
        """
        if self._intervals is not None:
            return self._intervals
        
        intervals = []
        
        with open(self.filepath) as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#') or line.startswith('track'):
                    continue
                
                # Parse BED fields (at least 3 columns: chrom, start, end)
                fields = line.split('\t')
                if len(fields) < 3:
                    continue
                
                try:
                    chrom = fields[0]
                    interval_start = int(fields[1])
                    interval_end = int(fields[2])
                    
                    intervals.append((chrom, interval_start, interval_end))
                except (ValueError, IndexError):
                    continue
        
        self._intervals = intervals
        return intervals
    
    def _get_filtered_intervals(
        self, 
        chrom: str, 
        start: int, 
        end: int
    ) -> List[Tuple[int, int]]:
        """
        Get intervals that overlap with the region.
        
        Args:
            chrom: Chromosome name
            start: Region start
            end: Region end
            
        Returns:
            List of (interval_start, interval_end) tuples, clipped to region
        """
        all_intervals = self._load_bed_file()
        
        filtered = []
        for interval_chrom, interval_start, interval_end in all_intervals:
            # Check chromosome match
            if interval_chrom != chrom:
                continue
            
            # Check overlap
            if interval_end <= start or interval_start >= end:
                continue
            
            # Clip to region bounds
            clipped_start = max(interval_start, start)
            clipped_end = min(interval_end, end)
            
            filtered.append((clipped_start, clipped_end))
        
        return filtered
    
    def _draw_boxes(self, ax: plt.Axes, intervals: List[Tuple[int, int]]) -> None:
        """
        Draw intervals as boxes at a fixed y-level.
        
        Args:
            ax: Matplotlib Axes
            intervals: List of (start, end) tuples
        """
        # Set y-limits for box display
        ax.set_ylim(0, 1)
        
        # Draw each interval as a rectangle
        for interval_start, interval_end in intervals:
            rect = mpatches.Rectangle(
                (interval_start, 0.1),
                interval_end - interval_start,
                0.8,
                facecolor=self.color,
                edgecolor='none',
                alpha=self.alpha
            )
            ax.add_patch(rect)
        
        # Remove y-axis
        ax.set_yticks([])
    
    def _draw_highlights(self, ax: plt.Axes, intervals: List[Tuple[int, int]]) -> None:
        """
        Draw intervals as full-height highlight bands.
        
        Args:
            ax: Matplotlib Axes
            intervals: List of (start, end) tuples
        """
        # Use axvspan for full-height highlighting
        for interval_start, interval_end in intervals:
            ax.axvspan(
                interval_start,
                interval_end,
                facecolor=self.color,
                alpha=self.alpha,
                edgecolor='none'
            )
        
        # Set generic y-limits
        ax.set_ylim(0, 1)
        ax.set_yticks([])

