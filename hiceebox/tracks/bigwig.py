"""BigWig track for continuous signal data."""

from typing import Tuple, Optional
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from hiceebox.tracks.base import Track


class BigWigTrack(Track):
    """
    Track for displaying continuous signal data from bigWig files.
    
    Displays signal as a filled area plot or line plot.
    """
    
    def __init__(
        self,
        filepath: str,
        name: Optional[str] = None,
        color: str = "#1a5276",
        alpha: float = 0.7,
        style: str = "fill",
        height: float = 1.0,
        pad_top: float = 0.05,
        pad_bottom: float = 0.05,
        ylim: Optional[Tuple[Optional[float], Optional[float]]] = None,
        show_ylim_labels: bool = True
    ):
        """
        Initialize BigWig track.
        
        Args:
            filepath: Path to bigWig file
            name: Track name (defaults to filename)
            color: Plot color
            alpha: Transparency (0-1)
            style: Plot style ('fill' or 'line')
            height: Relative height weight
            pad_top: Top padding fraction
            pad_bottom: Bottom padding fraction
            ylim: Y-axis limits (min, max). None = auto; (None, max) or (min, None) for partial auto.
            show_ylim_labels: If True, show min/max (and scale) on the left y-axis
        """
        track_name = name or Path(filepath).stem
        super().__init__(name=track_name, height=height, pad_top=pad_top, pad_bottom=pad_bottom)
        
        self.filepath = Path(filepath)
        self.color = color
        self.alpha = alpha
        self.style = style
        self.ylim = ylim
        self.show_ylim_labels = show_ylim_labels
        self._bw = None
        # Store actual ylim used in rendering (for display purposes)
        self.actual_ylim: Optional[Tuple[float, float]] = None
        
        self._validate_file()
    
    def _validate_file(self) -> None:
        """Validate that the file exists."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"BigWig file not found: {self.filepath}")
    
    def _get_bigwig(self):
        """
        Lazy-load pyBigWig object.
        
        Returns:
            pyBigWig object
        """
        if self._bw is None:
            try:
                import pyBigWig
            except ImportError:
                raise ImportError(
                    "pyBigWig library is required for bigWig files. "
                    "Install with: pip install pyBigWig"
                )
            
            self._bw = pyBigWig.open(str(self.filepath))
        
        return self._bw
    
    def draw(self, ax: plt.Axes, region: Tuple[str, int, int]) -> None:
        """
        Draw bigWig signal track.
        
        Fetches signal values from bigWig file and renders as a filled area or line plot.
        Automatically subsamples data based on region size to optimize performance.
        
        Args:
            ax: Matplotlib Axes to draw on
            region: Genomic region (chrom, start, end)
        """
        chrom, start, end = region
        
        try:
            # Fetch data
            positions, values = self._fetch_signal(chrom, start, end)
            
            if len(positions) == 0 or len(values) == 0:
                # No data in region
                ax.text(
                    0.5, 0.5,
                    f"No data in region",
                    transform=ax.transAxes,
                    ha='center', va='center',
                    fontsize=9, color='gray'
                )
                self.set_xlim(ax, start, end)
                self.format_axis(ax, show_xlabel=False)
                return
            
            # Plot signal
            self._plot_signal(ax, positions, values)
            
            # Set axis limits
            self.set_xlim(ax, start, end)
            
            # Set y-limits
            valid_values = values[~np.isnan(values)]
            
            # Check if ylim is None or tuple with both None (full auto)
            is_auto = self.ylim is None or (
                isinstance(self.ylim, tuple) and len(self.ylim) == 2 
                and self.ylim[0] is None and self.ylim[1] is None
            )
            
            if not is_auto and self.ylim is not None:
                # Manual ylim specified (can be tuple with None values for partial auto)
                if isinstance(self.ylim, tuple) and len(self.ylim) == 2:
                    ymin, ymax = self.ylim
                    # Handle partial None values (auto for one axis)
                    if len(valid_values) > 0:
                        if ymin is None:
                            ymin = 0  # Usually start from 0 for signal tracks
                        if ymax is None:
                            ymax = np.percentile(valid_values, 98) * 1.1
                    else:
                        # No valid data, use defaults
                        if ymin is None:
                            ymin = 0
                        if ymax is None:
                            ymax = 1
                    ax.set_ylim(ymin, ymax)
                    self.actual_ylim = (ymin, ymax)
                else:
                    # Invalid ylim format, fall back to auto
                    if len(valid_values) > 0:
                        ymin = 0
                        ymax = np.percentile(valid_values, 98) * 1.1
                        ax.set_ylim(ymin, ymax)
                        self.actual_ylim = (ymin, ymax)
                    else:
                        self.actual_ylim = None
            else:
                # Auto-scale with some padding
                if len(valid_values) > 0:
                    ymin = 0  # Usually start from 0 for signal tracks
                    ymax = np.percentile(valid_values, 98) * 1.1  # Add 10% padding
                    ax.set_ylim(ymin, ymax)
                    self.actual_ylim = (ymin, ymax)
                else:
                    self.actual_ylim = None
            
            # Show min/max on y-axis when requested
            if self.show_ylim_labels and self.actual_ylim is not None:
                ymin, ymax = self.actual_ylim
                ax.set_yticks([ymin, ymax])
                ax.tick_params(axis='y', labelleft=True, labelsize=7)
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2g}'))
            
        except Exception as e:
            # Handle errors gracefully
            ax.text(
                0.5, 0.5,
                f"Error loading bigWig:\n{str(e)}",
                transform=ax.transAxes,
                ha='center', va='center',
                fontsize=8, color='red'
            )
        
        self.format_axis(ax, show_xlabel=False)
    
    def _fetch_signal(
        self, 
        chrom: str, 
        start: int, 
        end: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fetch signal values from bigWig file with intelligent subsampling.
        
        Args:
            chrom: Chromosome name
            start: Start position
            end: End position
            
        Returns:
            tuple: (positions, values) arrays
        """
        bw = self._get_bigwig()
        
        # Check if chromosome exists in file
        if chrom not in bw.chroms():
            return np.array([]), np.array([])
        
        # Calculate appropriate number of bins
        # Target ~1000-2000 data points for smooth plotting
        region_size = end - start
        n_bins = min(2000, max(100, region_size // 100))
        
        # Fetch data using stats method for efficient summarization
        try:
            values = bw.stats(chrom, start, end, type="mean", nBins=n_bins)
            
            if values is None:
                return np.array([]), np.array([])
            
            # Convert to numpy array and replace None with NaN
            values = np.array([v if v is not None else np.nan for v in values])
            
            # Calculate bin positions (centers)
            bin_width = region_size / n_bins
            positions = np.linspace(
                start + bin_width / 2,
                end - bin_width / 2,
                n_bins
            )
            
            return positions, values
            
        except Exception:
            # Fallback: try to get values directly
            try:
                intervals = bw.intervals(chrom, start, end)
                if not intervals:
                    return np.array([]), np.array([])
                
                # Convert intervals to arrays
                positions = []
                values = []
                for interval_start, interval_end, value in intervals:
                    # Use midpoint of interval
                    positions.append((interval_start + interval_end) / 2)
                    values.append(value)
                
                return np.array(positions), np.array(values)
            except Exception:
                return np.array([]), np.array([])
    
    def _plot_signal(
        self, 
        ax: plt.Axes, 
        positions: np.ndarray, 
        values: np.ndarray
    ) -> None:
        """
        Plot signal data on axes.
        
        Args:
            ax: Matplotlib Axes
            positions: Genomic positions
            values: Signal values
        """
        # Replace NaN with 0 for plotting
        plot_values = values.copy()
        plot_values[np.isnan(plot_values)] = 0
        
        if self.style == 'fill':
            # Filled area plot
            ax.fill_between(
                positions,
                plot_values,
                0,
                color=self.color,
                alpha=self.alpha,
                linewidth=0,
                step='mid'
            )
        else:
            # Line plot
            ax.plot(
                positions,
                plot_values,
                color=self.color,
                alpha=self.alpha,
                linewidth=1.0
            )
    
    def __del__(self):
        """Close bigWig file on deletion."""
        if self._bw is not None:
            self._bw.close()

