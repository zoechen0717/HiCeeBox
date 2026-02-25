"""
Viewer state management for HiCeeBox GUI.

This module implements the ViewerState class that tracks the entire state
of the genome browser, including loaded files, current region, and track visibility.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TrackConfig:
    """
    Configuration for a single track.
    
    Attributes:
        track_type: Type of track ('hic', 'bigwig', 'bed', 'bedpe', 'gene')
        filepath: Path to the data file
        visible: Whether track is currently visible
        name: Display name for the track
        options: Additional track-specific options (color, height, etc.)
    """
    track_type: str  # 'hic', 'bigwig', 'bed', 'bedpe', 'gene'
    filepath: str
    visible: bool = True
    name: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default name from filepath if not provided."""
        if self.name is None:
            self.name = Path(self.filepath).stem


class ViewerState:
    """
    Central state manager for the genome browser.
    
    Manages:
    - Loaded data files (Hi-C, BigWig, BED, BEDPE, genes)
    - Current genomic region being viewed
    - Track visibility and ordering
    - Navigation state (zoom, pan)
    """
    
    def __init__(
        self,
        chrom: str = "chr1",
        start: int = 1_000_000,
        end: int = 2_000_000,
        resolution: int = 10_000
    ):
        """
        Initialize viewer state.
        
        Args:
            chrom: Initial chromosome
            start: Initial region start position
            end: Initial region end position
            resolution: Hi-C matrix resolution in base pairs
        """
        # Genomic region
        self.chrom = chrom
        self.start = start
        self.end = end
        self.resolution = resolution
        
        # Data sources
        self.hic_file: Optional[str] = None
        self.tracks: List[TrackConfig] = []
        self._last_hic_track: Optional[Any] = None  # Reference to last rendered Hi-C track
        
        # Hi-C display settings
        self.normalization: str = "NONE"
        self.vmin: Optional[float] = None
        self.vmax: Optional[float] = None
        self.cmap: str = "OrRd"  # Darker default than Reds
        self.show_colorbar: bool = False
        self.auto_resolution: bool = True
        self.available_resolutions: List[int] = []  # Will be populated when file is loaded
        
        # Viewer settings
        self.figure_width = 12.0  # inches
        self.figure_dpi = 150
    
    @property
    def region_size(self) -> int:
        """Get current region size in base pairs."""
        return self.end - self.start
    
    def region_string(self) -> str:
        """
        Get canonical region string.
        
        Returns:
            String in format 'chr:start-end' with comma separators
        """
        return f"{self.chrom}:{self.start:,}-{self.end:,}"
    
    def set_region(self, chrom: str, start: int, end: int) -> None:
        """
        Set genomic region directly.
        
        Args:
            chrom: Chromosome name
            start: Start position
            end: End position
        """
        self.chrom = chrom
        self.start = max(0, start)
        self.end = max(self.start + 1000, end)  # Minimum 1kb region
    
    def zoom(self, factor: float) -> None:
        """
        Zoom in or out, centered on region midpoint.
        
        Args:
            factor: Zoom factor (>1 zooms in, <1 zooms out)
                   e.g., 2.0 halves the region size (zoom in 2x)
                        0.5 doubles the region size (zoom out 2x)
        """
        if factor <= 0:
            raise ValueError("Zoom factor must be positive")
        
        midpoint = (self.start + self.end) // 2
        current_size = self.region_size
        new_size = int(current_size / factor)
        
        # Ensure minimum size
        new_size = max(1000, new_size)
        
        # Calculate new boundaries
        half_size = new_size // 2
        self.start = max(0, midpoint - half_size)
        self.end = self.start + new_size
    
    def pan(self, bp: int) -> None:
        """
        Pan left or right by specified base pairs.
        
        Args:
            bp: Number of base pairs to pan (positive = right, negative = left)
        """
        region_size = self.region_size
        self.start = max(0, self.start + bp)
        self.end = self.start + region_size
    
    def add_track(self, track_config: TrackConfig) -> None:
        """
        Add a track to the viewer.
        
        Args:
            track_config: Track configuration
        """
        self.tracks.append(track_config)
    
    def remove_track(self, index: int) -> None:
        """
        Remove track at given index.
        
        Args:
            index: Index of track to remove
        """
        if 0 <= index < len(self.tracks):
            self.tracks.pop(index)
    
    def toggle_track_visibility(self, index: int) -> None:
        """
        Toggle visibility of track at given index.
        
        Args:
            index: Index of track to toggle
        """
        if 0 <= index < len(self.tracks):
            self.tracks[index].visible = not self.tracks[index].visible
    
    def get_visible_tracks(self) -> List[TrackConfig]:
        """
        Get list of currently visible tracks.
        
        Returns:
            List of TrackConfig objects where visible=True
        """
        return [track for track in self.tracks if track.visible]
    
    def clear_tracks(self) -> None:
        """Remove all tracks."""
        self.tracks.clear()

