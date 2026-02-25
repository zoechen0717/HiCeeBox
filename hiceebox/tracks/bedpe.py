"""BEDPE track for paired genomic intervals."""

from typing import Tuple, Optional, List
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from hiceebox.tracks.base import Track


class BedPETrack(Track):
    """
    Track for displaying paired genomic intervals from BEDPE files.
    
    Displays paired intervals as arcs or lines connecting two positions.
    """
    
    def __init__(
        self,
        filepath: str,
        name: Optional[str] = None,
        color: str = "#0d1b2a",
        alpha: float = 0.5,
        style: str = "arc",
        height: float = 1.0,
        scale: float = 1.0,
        pad_top: float = 0.05,
        pad_bottom: float = 0.05,
        max_arcs: int = 500,
        invert: bool = False
    ):
        """
        Initialize BEDPE track.
        
        Args:
            filepath: Path to BEDPE file
            name: Track name (defaults to filename)
            color: Feature color
            alpha: Transparency (0-1)
            style: Display style ('arc' or 'line')
            height: Relative height weight
            scale: Height multiplier (effective height = height * scale)
            pad_top: Top padding fraction
            pad_bottom: Bottom padding fraction
            max_arcs: Maximum number of arcs to display (to avoid clutter)
            invert: If True, draw arcs/lines inverted (arcs point downward)
        """
        track_name = name or Path(filepath).stem
        super().__init__(name=track_name, height=height, scale=scale, pad_top=pad_top, pad_bottom=pad_bottom)
        
        self.filepath = Path(filepath)
        self.color = color
        self.alpha = alpha
        self.style = style
        self.max_arcs = max_arcs
        self.invert = invert
        
        self._interactions = None  # Cached interactions
        
        self._validate_file()
    
    def _validate_file(self) -> None:
        """Validate that the file exists."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"BEDPE file not found: {self.filepath}")
    
    def draw(self, ax: plt.Axes, region: Tuple[str, int, int]) -> None:
        """
        Draw BEDPE interactions as arcs or lines.
        
        Parses BEDPE file, filters interactions overlapping the region, and renders
        them as curved arcs or straight lines connecting paired intervals.
        
        Args:
            ax: Matplotlib Axes to draw on
            region: Genomic region (chrom, start, end)
        """
        chrom, start, end = region
        
        try:
            # Load and filter interactions
            interactions = self._get_filtered_interactions(chrom, start, end)
            
            if len(interactions) == 0:
                # No interactions in region
                ax.text(
                    0.5, 0.5,
                    f"No interactions in region",
                    transform=ax.transAxes,
                    ha='center', va='center',
                    fontsize=9, color='gray'
                )
                ax.set_ylim(0, 1)
            else:
                # Limit number of arcs to avoid clutter
                if len(interactions) > self.max_arcs:
                    # Keep strongest/longest interactions
                    # Sort by distance and keep top max_arcs
                    interactions = sorted(
                        interactions,
                        key=lambda x: abs(x[2] - x[0]),
                        reverse=True
                    )[:self.max_arcs]
                
                # Render interactions
                if self.style == 'arc':
                    self._draw_arcs(ax, interactions)
                else:
                    self._draw_lines(ax, interactions)
            
        except Exception as e:
            # Handle errors gracefully
            ax.text(
                0.5, 0.5,
                f"Error loading BEDPE:\n{str(e)}",
                transform=ax.transAxes,
                ha='center', va='center',
                fontsize=8, color='red'
            )
            ax.set_ylim(0, 1)
        
        self.set_xlim(ax, start, end)
        self.format_axis(ax, show_xlabel=False)
    
    def _load_bedpe_file(self) -> List[Tuple[str, int, int, str, int, int]]:
        """
        Load BEDPE file and parse interactions.
        
        Returns:
            List of (chrom1, start1, end1, chrom2, start2, end2) tuples
        """
        if self._interactions is not None:
            return self._interactions
        
        interactions = []
        
        with open(self.filepath) as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#') or line.startswith('track'):
                    continue
                
                # Parse BEDPE fields (at least 6 columns)
                fields = line.split('\t')
                if len(fields) < 6:
                    continue
                
                try:
                    chrom1 = fields[0]
                    start1 = int(fields[1])
                    end1 = int(fields[2])
                    chrom2 = fields[3]
                    start2 = int(fields[4])
                    end2 = int(fields[5])
                    
                    interactions.append((chrom1, start1, end1, chrom2, start2, end2))
                except (ValueError, IndexError):
                    continue
        
        self._interactions = interactions
        return interactions
    
    def _get_filtered_interactions(
        self, 
        chrom: str, 
        start: int, 
        end: int
    ) -> List[Tuple[int, int, int, int]]:
        """
        Get interactions that overlap with the region.
        
        For now, only returns intra-chromosomal interactions.
        
        Args:
            chrom: Chromosome name
            start: Region start
            end: Region end
            
        Returns:
            List of (start1, end1, start2, end2) tuples for interactions
        """
        all_interactions = self._load_bedpe_file()
        
        filtered = []
        for chrom1, start1, end1, chrom2, start2, end2 in all_interactions:
            # Only intra-chromosomal interactions
            if chrom1 != chrom or chrom2 != chrom:
                continue
            
            # Check if either end overlaps with region
            overlap1 = not (end1 <= start or start1 >= end)
            overlap2 = not (end2 <= start or start2 >= end)
            
            if overlap1 or overlap2:
                # Use midpoints of intervals
                mid1 = (start1 + end1) // 2
                mid2 = (start2 + end2) // 2
                
                # Include if at least one anchor overlaps the region
                # This allows visualization of loops that extend beyond the region
                filtered.append((start1, end1, start2, end2))
        
        return filtered
    
    def _draw_arcs(
        self, 
        ax: plt.Axes, 
        interactions: List[Tuple[int, int, int, int]]
    ) -> None:
        """
        Draw interactions as curved arcs.
        
        Args:
            ax: Matplotlib Axes
            interactions: List of (start1, end1, start2, end2) tuples
        """
        if not interactions:
            return
        
        # Calculate max arc height for scaling
        max_distance = max(
            abs((s2 + e2) / 2 - (s1 + e1) / 2)
            for s1, e1, s2, e2 in interactions
        )
        
        # Set y-limits
        max_height = 1.0
        ax.set_ylim(0, max_height)
        
        # Draw each interaction as an arc
        for start1, end1, start2, end2 in interactions:
            mid1 = (start1 + end1) / 2
            mid2 = (start2 + end2) / 2
            
            # Ensure x1 < x2
            x1, x2 = min(mid1, mid2), max(mid1, mid2)
            
            # Calculate arc height proportional to distance
            distance = x2 - x1
            height = (distance / max_distance) * max_height * 0.9
            
            # Create arc using bezier-like curve
            n_points = 50
            x_points = np.linspace(x1, x2, n_points)
            
            # Parabolic arc (invert: draw downward)
            t = np.linspace(0, 1, n_points)
            y_points = 4 * height * t * (1 - t)
            if self.invert:
                y_points = max_height - y_points  # arc bulges downward
            # Draw the arc
            ax.plot(
                x_points,
                y_points,
                color=self.color,
                alpha=self.alpha,
                linewidth=0.5
            )
        # Remove y-axis
        ax.set_yticks([])
    
    def _draw_lines(
        self, 
        ax: plt.Axes, 
        interactions: List[Tuple[int, int, int, int]]
    ) -> None:
        """
        Draw interactions as straight lines.
        
        Args:
            ax: Matplotlib Axes
            interactions: List of (start1, end1, start2, end2) tuples
        """
        # Set y-limits
        ax.set_ylim(0, 1)
        if self.invert:
            ax.invert_yaxis()
        
        # Draw each interaction as a line at mid-height
        y_pos = 0.5
        
        for start1, end1, start2, end2 in interactions:
            mid1 = (start1 + end1) / 2
            mid2 = (start2 + end2) / 2
            
            ax.plot(
                [mid1, mid2],
                [y_pos, y_pos],
                color=self.color,
                alpha=self.alpha,
                linewidth=1.0
            )
        
        # Remove y-axis
        ax.set_yticks([])

