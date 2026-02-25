"""Hi-C triangle heatmap track."""

from typing import Tuple, Optional
import matplotlib.pyplot as plt
import numpy as np

from hiceebox.tracks.base import Track
from hiceebox.matrix.base import MatrixProvider


class HiCTriangleTrack(Track):
    """
    Track for displaying Hi-C contact matrix as a triangle heatmap.
    
    Displays the upper triangle of the contact matrix rotated 45 degrees
    to align with linear genomic coordinates below.
    """
    
    def __init__(
        self,
        matrix_provider: MatrixProvider,
        resolution: int,
        norm: str = "KR",
        cmap: str = "OrRd",
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        show_colorbar: bool = False,
        name: Optional[str] = "Hi-C",
        height: float = 2.0,
        pad_top: float = 0.05,
        pad_bottom: float = 0.05
    ):
        """
        Initialize Hi-C triangle track.
        
        Args:
            matrix_provider: MatrixProvider instance for fetching Hi-C data
            resolution: Bin size in base pairs
            norm: Normalization method (e.g., 'KR', 'VC', 'NONE')
            cmap: Matplotlib colormap name (e.g. 'Reds', 'YlOrRd')
            vmin: Minimum value for color scale (None = auto, use 0)
            vmax: Maximum value for color scale (None = auto, use 99th percentile)
            show_colorbar: If True, draw a colorbar for the heatmap scale
            name: Track name
            height: Relative height weight
            pad_top: Top padding fraction
            pad_bottom: Bottom padding fraction
        """
        super().__init__(name=name, height=height, pad_top=pad_top, pad_bottom=pad_bottom)
        self.matrix_provider = matrix_provider
        self.resolution = resolution
        self.norm = norm
        self.cmap = cmap
        self.vmin = vmin
        self.vmax = vmax
        self.show_colorbar = show_colorbar
        # Store actual vmin/vmax used in rendering (for display purposes)
        self.actual_vmin: Optional[float] = None
        self.actual_vmax: Optional[float] = None
    
    def draw(
        self,
        ax: plt.Axes,
        region: Tuple[str, int, int],
        cached_matrix: Optional[np.ndarray] = None,
        cached_bins: Optional[np.ndarray] = None,
    ) -> None:
        """
        Draw Hi-C triangle heatmap.
        
        Renders the upper triangle of the Hi-C contact matrix rotated 45 degrees
        to align with the genomic x-axis. Uses provider fetch or cached_matrix/bins.
        
        Args:
            ax: Matplotlib Axes to draw on
            region: Genomic region (chrom, start, end)
            cached_matrix: Optional pre-fetched matrix (skips fetch when set)
            cached_bins: Optional pre-fetched bins (must pair with cached_matrix)
        """
        chrom, start, end = region
        
        try:
            if cached_matrix is not None and cached_bins is not None:
                matrix, bins = cached_matrix, cached_bins
            else:
                matrix, bins = self.matrix_provider.fetch(
                    chrom, start, end, self.resolution, self.norm
                )
            
            if matrix.size == 0 or len(bins) == 0:
                # No data in region
                ax.text(
                    0.5, 0.5,
                    f"No Hi-C data in region",
                    transform=ax.transAxes,
                    ha='center', va='center',
                    fontsize=9, color='gray'
                )
                self.set_xlim(ax, start, end)
                self.format_axis(ax, show_xlabel=False)
                return
            
            # Preprocess matrix
            matrix_processed = self._preprocess_matrix(matrix)
            
            # Render triangle
            self._render_triangle(ax, matrix_processed, bins, start, end)
            
        except Exception as e:
            # Handle errors gracefully
            ax.text(
                0.5, 0.5,
                f"Error loading Hi-C data:\n{str(e)}",
                transform=ax.transAxes,
                ha='center', va='center',
                fontsize=8, color='red'
            )
        
        self.set_xlim(ax, start, end)
        self.format_axis(ax, show_xlabel=False)
    
    def _preprocess_matrix(self, matrix: np.ndarray) -> np.ndarray:
        """
        Preprocess contact matrix before visualization.
        
        Applies log transformation and handles zeros/NaNs.
        
        Args:
            matrix: Raw contact matrix
            
        Returns:
            Preprocessed matrix ready for visualization
        """
        # Copy to avoid modifying original
        mat = matrix.copy()
        
        # Replace zeros and negatives with NaN for cleaner visualization
        mat[mat <= 0] = np.nan
        
        # Log transform (log10(x + 1) to handle low values)
        mat = np.log10(mat + 1)
        
        return mat
    
    def _render_triangle(
        self, 
        ax: plt.Axes, 
        matrix: np.ndarray, 
        bins: np.ndarray,
        region_start: int,
        region_end: int
    ) -> None:
        """
        Render Hi-C matrix as a rotated triangle.
        
        Uses a coordinate transformation to rotate the square matrix 45 degrees
        and display only the upper triangle aligned with genomic coordinates.
        
        Args:
            ax: Matplotlib Axes
            matrix: Preprocessed contact matrix
            bins: Bin start positions
            region_start: Region start position
            region_end: Region end position
        """
        n = len(bins)
        matrix_shape = matrix.shape
        
        if n < 2:
            return
        
        # Ensure matrix dimensions match bins length
        if matrix_shape[0] != n or matrix_shape[1] != n:
            # Matrix and bins size mismatch - use minimum size
            min_size = min(n, matrix_shape[0], matrix_shape[1])
            if min_size < 2:
                return
            # Truncate to match
            bins = bins[:min_size]
            matrix = matrix[:min_size, :min_size]
            n = min_size
        
        # Create meshgrid for the matrix
        # We'll transform coordinates to create triangle effect
        
        # Calculate bin centers and width
        if len(bins) >= 2:
            bin_width = bins[1] - bins[0]
        else:
            bin_width = self.resolution
        
        # For triangle visualization, we need to transform each cell
        # We'll use pcolormesh with custom coordinates
        
        # Create coordinate arrays for triangle transformation
        # For each point (i, j) in the matrix, map to (x, y) where:
        # x = (i + j) * bin_width / 2 + bins[0]  (genomic position)
        # y = (j - i) * bin_width / 2            (height in triangle)
        
        # Pre-compute coordinates for pcolormesh
        x_coords = []
        y_coords = []
        colors = []
        
        max_height = n * bin_width / 2
        
        # Iterate through upper triangle
        for i in range(n):
            for j in range(i, n):
                # Ensure indices are within matrix bounds
                if i >= matrix.shape[0] or j >= matrix.shape[1]:
                    continue
                
                # Genomic center position
                x_center = bins[i] + (bins[j] - bins[i]) / 2 + bin_width / 2
                
                # Height in triangle (distance from diagonal)
                y_height = (j - i) * bin_width / 2
                
                # Only plot if within reasonable bounds
                if x_center >= region_start and x_center <= region_end:
                    value = matrix[i, j]
                    if not np.isnan(value):
                        x_coords.append(x_center)
                        y_coords.append(y_height)
                        colors.append(value)
        
        if not colors:
            # No valid data
            ax.set_ylim(0, 1)
            return
        
        # Plot using scatter with square markers for pixel effect
        # Calculate marker size based on bin width and axes dimensions
        colors_array = np.array(colors)
        
        # Determine color limits
        # For Hi-C data, we want to show enrichment more prominently
        if self.vmin is not None:
            vmin = self.vmin
        else:
            # For Hi-C, typically start from 0 to show full dynamic range
            vmin = 0
        
        if self.vmax is not None:
            vmax = self.vmax
        else:
            # Use 99th percentile to make enrichment more visible
            # This ensures high enrichment values are displayed prominently
            # and prevents outliers from compressing the color scale
            vmax = np.nanpercentile(colors_array, 99)
            
            # If 99th percentile is too low compared to max, use a more aggressive approach
            max_val = np.nanmax(colors_array)
            if max_val > vmax * 1.5:
                # If there are very high outliers, use 98th percentile instead
                # This will make more values show as high enrichment
                vmax = np.nanpercentile(colors_array, 98)
        
        # Store actual values used (for UI display)
        self.actual_vmin = vmin
        self.actual_vmax = vmax
        
        # Create scatter plot for triangle effect
        # Use marker size proportional to resolution
        markersize = 2  # Will adjust based on resolution/width ratio
        
        scatter = ax.scatter(
            x_coords,
            y_coords,
            c=colors,
            cmap=self.cmap,
            vmin=vmin,
            vmax=vmax,
            marker='s',
            s=markersize,
            edgecolors='none',
            rasterized=True  # Rasterize for better PDF performance
        )
        
        if self.show_colorbar:
            fig = ax.get_figure()
            cbar = fig.colorbar(scatter, ax=ax, shrink=0.6, aspect=20, pad=0.02)
            cbar.set_label("log10(contact + 1)", fontsize=8)
        
        # Set y-axis limits
        ax.set_ylim(0, max_height)
        
        # Hide y-axis
        ax.set_yticks([])
        ax.set_ylabel('')

