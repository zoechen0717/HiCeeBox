"""
Controller and data management for HiCeeBox GUI.

This module implements the DataManager class that handles caching of open file handles
and the rendering controller that bridges the GUI and the core hiceebox library.
"""

from typing import Dict, Optional, Any, Tuple
from pathlib import Path
import numpy as np
import matplotlib.figure

from hiceebox.matrix.base import MatrixProvider
from hiceebox.matrix.hic_provider import HicMatrixProvider
from hiceebox.matrix.cooler_provider import CoolerMatrixProvider
from hiceebox.view.genome_view import GenomeView
from hiceebox.view.layout import LayoutManager
from hiceebox.tracks import (
    HiCTriangleTrack,
    HiCGenomeViewTrack,
    BigWigTrack,
    BedTrack,
    BedPETrack,
    GeneTrack
)

from hiceebox_gui.state import ViewerState, TrackConfig

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    QApplication = None


class DataManager:
    """
    Manages cached file handles for genomic data files.
    
    Keeps file handles open to avoid repeated I/O operations.
    """
    
    def __init__(self):
        """Initialize data manager with empty caches."""
        self._matrix_providers: Dict[str, MatrixProvider] = {}
        self._file_cache: Dict[str, Any] = {}
    
    def get_matrix_provider(
        self, 
        filepath: str, 
        resolution: Optional[int] = None
    ) -> MatrixProvider:
        """
        Get or create a matrix provider for Hi-C data.
        
        Args:
            filepath: Path to .hic or .mcool file
            resolution: Resolution for .mcool files
            
        Returns:
            MatrixProvider instance
        """
        cache_key = f"{filepath}:{resolution}" if resolution else filepath
        
        if cache_key not in self._matrix_providers:
            path = Path(filepath)
            
            if path.suffix == '.hic':
                self._matrix_providers[cache_key] = HicMatrixProvider(filepath)
            elif path.suffix in ['.mcool', '.cool']:
                if resolution is None:
                    raise ValueError("Resolution required for .mcool files")
                self._matrix_providers[cache_key] = CoolerMatrixProvider(
                    filepath, resolution=resolution
                )
            else:
                raise ValueError(f"Unsupported Hi-C file format: {path.suffix}")
        
        return self._matrix_providers[cache_key]
    
    def clear_cache(self) -> None:
        """Clear all cached file handles."""
        self._matrix_providers.clear()
        self._file_cache.clear()


class RenderController:
    """
    Controller that renders genomic views using the core hiceebox library.
    
    Bridges the GUI state to the plotting backend.
    """
    
    def __init__(self, data_manager: Optional[DataManager] = None):
        """
        Initialize render controller.
        
        Args:
            data_manager: DataManager instance (creates new if None)
        """
        self.data_manager = data_manager or DataManager()
        # Cache for Hi-C matrix when region unchanged (key, matrix, bins)
        self._hic_cache: Optional[Tuple[Tuple[str, int, int, int], np.ndarray, np.ndarray]] = None
    
    def render(
        self,
        viewer_state: ViewerState,
        figure: Optional[matplotlib.figure.Figure] = None,
        preview: bool = False,
    ) -> matplotlib.figure.Figure:
        """
        Render the current viewer state to a matplotlib figure.

        Args:
            viewer_state: Current viewer state
            figure: Existing figure to render into (creates new if None)
            preview: If True, use lower DPI and allow UI updates during draw

        Returns:
            Matplotlib Figure object with rendered tracks
        """
        dpi = viewer_state.figure_dpi
        if preview and figure is not None:
            dpi = min(100, viewer_state.figure_dpi)
        # Create GenomeView
        gv = GenomeView(
            chrom=viewer_state.chrom,
            start=viewer_state.start,
            end=viewer_state.end,
            width=viewer_state.figure_width,
            dpi=dpi
        )
        
        # Add Hi-C track if available
        if viewer_state.hic_file:
            try:
                matrix_provider = self.data_manager.get_matrix_provider(
                    viewer_state.hic_file,
                    resolution=viewer_state.resolution
                )
                
                # When rendering to existing figure, we draw colorbar in reserved space for alignment
                show_cb_in_track = viewer_state.show_colorbar and (figure is None)
                hic_track = HiCTriangleTrack(
                    matrix_provider=matrix_provider,
                    resolution=viewer_state.resolution,
                    norm=viewer_state.normalization,
                    vmin=viewer_state.vmin,
                    vmax=viewer_state.vmax,
                    name='Hi-C',
                    height=2.5,
                    cmap=viewer_state.cmap,
                    show_colorbar=show_cb_in_track
                )
                
                gv.add_track(hic_track)
                # Store track reference for later access to actual vmin/vmax
                viewer_state._last_hic_track = hic_track
            except Exception as e:
                import traceback
                error_msg = f"Failed to load Hi-C track: {e}"
                print(error_msg)
                traceback.print_exc()
                # Still add a placeholder so the view renders, but shows error message
                # The track itself will display the error message in its draw() method
        
        # Add other tracks
        for track_config in viewer_state.get_visible_tracks():
            try:
                track = self._create_track(track_config, viewer_state.resolution)
                if track:
                    gv.add_track(track)
            except Exception as e:
                print(f"Warning: Failed to load track {track_config.name}: {e}")
        
        # Render to figure
        if figure is None:
            # No existing figure, use GenomeView.plot() which creates a new one
            return gv.plot(output=None, show=False, close=False)
        else:
            # Render to existing figure by manually creating layout and drawing
            figure.clear()
            if not gv.tracks:
                figure.set_size_inches(gv.width, 4.0)
                figure.set_dpi(gv.dpi)
                return figure
            
            import matplotlib.gridspec as gridspec
            
            # When showing colorbar, use 2 columns so all track axes stay aligned (colorbar in col 1, row 0 only)
            use_colorbar_layout = bool(
                viewer_state.show_colorbar and viewer_state.hic_file and gv.tracks
            )
            ncols = 2 if use_colorbar_layout else 1
            width_ratios = [1.0, 0.04] if use_colorbar_layout else [1.0]
            
            # Calculate heights
            height_ratios = []
            for track in gv.tracks:
                effective_height = track.height * (1.0 + track.pad_top + track.pad_bottom)
                height_ratios.append(effective_height)
            
            total_weight = sum(height_ratios)
            base_height_per_unit = 2.0
            total_height = total_weight * base_height_per_unit + 0.3 * (len(gv.tracks) - 1)
            
            figure.set_size_inches(gv.width, total_height)
            figure.set_dpi(gv.dpi)
            
            gs = gridspec.GridSpec(
                nrows=len(gv.tracks),
                ncols=ncols,
                figure=figure,
                height_ratios=height_ratios,
                width_ratios=width_ratios,
                hspace=0.1,
                wspace=0.02
            )
            
            axes = []
            hic_cache_key = (
                viewer_state.hic_file or "",
                viewer_state.chrom,
                viewer_state.start,
                viewer_state.end,
                viewer_state.resolution,
            )
            if self._hic_cache is not None and self._hic_cache[0] != hic_cache_key:
                self._hic_cache = None
            for i, track in enumerate(gv.tracks):
                ax = figure.add_subplot(gs[i, 0])
                # Use Hi-C cache when region unchanged (first track is Hi-C)
                if (
                    i == 0
                    and viewer_state.hic_file
                    and isinstance(track, HiCTriangleTrack)
                    and self._hic_cache is not None
                    and self._hic_cache[0] == hic_cache_key
                ):
                    track.draw(
                        ax,
                        gv.region,
                        cached_matrix=self._hic_cache[1],
                        cached_bins=self._hic_cache[2],
                    )
                elif (
                    i == 0
                    and viewer_state.hic_file
                    and isinstance(track, HiCTriangleTrack)
                ):
                    matrix_provider = self.data_manager.get_matrix_provider(
                        viewer_state.hic_file,
                        resolution=viewer_state.resolution,
                    )
                    matrix, bins = matrix_provider.fetch(
                        viewer_state.chrom,
                        viewer_state.start,
                        viewer_state.end,
                        viewer_state.resolution,
                        viewer_state.normalization,
                    )
                    self._hic_cache = (hic_cache_key, matrix, np.asarray(bins))
                    track.draw(
                        ax,
                        gv.region,
                        cached_matrix=matrix,
                        cached_bins=self._hic_cache[2],
                    )
                else:
                    track.draw(ax, gv.region)
                axes.append(ax)
                if preview and QApplication is not None:
                    QApplication.processEvents()
            
            # Draw colorbar in reserved column so Hi-C and other tracks stay aligned
            if use_colorbar_layout and axes:
                ax0 = axes[0]
                if ax0.collections:
                    cax = figure.add_subplot(gs[0, 1])
                    cbar = figure.colorbar(ax0.collections[0], cax=cax)
                    cbar.set_label("log10(contact + 1)", fontsize=8)
            
            if axes:
                bottom_ax = axes[-1]
                bottom_ax.set_xlabel(
                    f"{gv.chrom}:{gv.start:,}-{gv.end:,} ({gv.region_size:,} bp)",
                    fontsize=10
                )
                bottom_ax.tick_params(labelbottom=True)
            
            if gv.title:
                figure.suptitle(gv.title, fontsize=12, y=0.98)

            figure.tight_layout()
            return figure
    
    def _create_track(self, track_config: TrackConfig, resolution: int):
        """
        Create a track object from configuration.
        
        Args:
            track_config: Track configuration
            resolution: Hi-C resolution (for Hi-C tracks)
            
        Returns:
            Track instance or None if creation fails
        """
        filepath = track_config.filepath
        options = track_config.options
        
        if track_config.track_type == 'hic':
            matrix_provider = self.data_manager.get_matrix_provider(
                filepath, resolution=resolution
            )
            return HiCTriangleTrack(
                matrix_provider=matrix_provider,
                resolution=resolution,
                name=track_config.name,
                **options
            )
        
        elif track_config.track_type == 'bigwig':
            # Extract ylim from options if present (don't pop, keep it for options dict)
            ylim = options.get('ylim', None)
            # Create a copy of options without ylim to pass separately
            track_options = {k: v for k, v in options.items() if k != 'ylim'}
            return BigWigTrack(
                filepath=filepath,
                name=track_config.name,
                ylim=ylim,
                **track_options
            )
        
        elif track_config.track_type == 'bed':
            return BedTrack(
                filepath=filepath,
                name=track_config.name,
                **options
            )
        
        elif track_config.track_type == 'bedpe':
            return BedPETrack(
                filepath=filepath,
                name=track_config.name,
                **options
            )
        
        elif track_config.track_type == 'gene':
            return GeneTrack(
                filepath=filepath,
                name=track_config.name,
                **options
            )
        
        else:
            print(f"Unknown track type: {track_config.track_type}")
            return None

