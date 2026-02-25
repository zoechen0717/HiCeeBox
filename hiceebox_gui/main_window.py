"""
Main window for HiCeeBox GUI application.

Implements the primary application window with IGV/Juicebox-style layout.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStatusBar, QDockWidget, QFileDialog,
    QMessageBox, QDialog, QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal
from pathlib import Path

from hiceebox_gui.state import ViewerState, TrackConfig
from hiceebox_gui.controller import RenderController, DataManager
from hiceebox_gui.canvas import GenomeCanvas
from hiceebox_gui.widgets import NavigationBar, TrackPanel, TrackPropertiesDialog


class LoadHiCWorker(QThread):
    """Background worker to load Hi-C file and metadata without blocking UI."""
    finished = Signal(object)  # (result_dict or None, error_str or None)

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            from pathlib import Path
            from hiceebox.matrix.hic_provider import HicMatrixProvider
            from hiceebox.matrix.cooler_provider import CoolerMatrixProvider

            path = Path(self.filepath)
            if path.suffix == ".mcool":
                import cooler
                resolutions_raw = cooler.fileops.list_coolers(str(self.filepath))
                resolution_values = sorted(
                    int(uri.split("/")[-1]) for uri in (resolutions_raw or [])
                )
                max_resolution = max(resolution_values) if resolution_values else None
                matrix_provider = CoolerMatrixProvider(
                    self.filepath, resolution=max_resolution
                )
            else:
                matrix_provider = HicMatrixProvider(self.filepath)
            resolutions = list(matrix_provider.get_resolutions()) if matrix_provider else []
            chromosomes = list(matrix_provider.get_chromosomes()) if matrix_provider else []
            res = sorted(resolutions) if resolutions else []
            if not res:
                self.finished.emit((None, "No resolutions available"))
                return
            default_res = 10_000 if 10_000 in res else min(res)
            target_chrom = "chr1"
            if chromosomes and target_chrom not in chromosomes:
                for c in chromosomes:
                    if c.upper() in ("CHR1", "1"):
                        target_chrom = c
                        break
                else:
                    target_chrom = chromosomes[0]
            self.finished.emit(
                (
                    {
                        "filepath": self.filepath,
                        "matrix_provider": matrix_provider,
                        "resolutions": res,
                        "chromosomes": chromosomes,
                        "default_resolution": default_res,
                        "target_chrom": target_chrom,
                        "region_start": 2_171_487,
                        "region_end": 2_954_337,
                    },
                    None,
                )
            )
        except Exception as e:
            self.finished.emit((None, str(e)))


class MainWindow(QMainWindow):
    """
    Main application window for HiCeeBox genome browser.
    
    Layout:
    - Top: Navigation bar (chromosome, coordinates, zoom/pan)
    - Left: Track panel (dockable)
    - Center: Matplotlib canvas for rendering
    - Bottom: Control buttons (Preview, Export)
    """
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        # Initialize state and controller
        self.viewer_state = ViewerState(
            chrom="chr1",
            start=1_000_000,
            end=2_000_000,
            resolution=10_000
        )
        self.data_manager = DataManager()
        self.render_controller = RenderController(self.data_manager)
        self._hic_load_worker = None

        self._setup_ui()
        self._connect_signals()
        
        self.setWindowTitle("HiCeeBox - Interactive Genome Browser")
        # Default size that shows all options (two-row nav + tracks + buttons)
        self.resize(1600, 1000)
        self.setMinimumSize(800, 600)
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Central widget (resizable with window)
        central_widget = QWidget()
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(central_widget)
        central_layout = QVBoxLayout(central_widget)
        
        # Navigation bar at top
        self.nav_bar = NavigationBar()
        central_layout.addWidget(self.nav_bar)
        
        # Matplotlib canvas (center), resizes with window
        self.canvas = GenomeCanvas(self, width=12, height=8, dpi=100)
        central_layout.addWidget(self.canvas, 1)
        
        # Bottom control buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.preview_btn = QPushButton("🔍 Preview")
        self.preview_btn.setMinimumWidth(120)
        self.preview_btn.setMinimumHeight(35)
        button_layout.addWidget(self.preview_btn)
        
        self.export_png_btn = QPushButton("💾 Export PNG")
        self.export_png_btn.setMinimumWidth(120)
        self.export_png_btn.setMinimumHeight(35)
        button_layout.addWidget(self.export_png_btn)
        
        self.export_pdf_btn = QPushButton("📄 Export PDF")
        self.export_pdf_btn.setMinimumWidth(120)
        self.export_pdf_btn.setMinimumHeight(35)
        button_layout.addWidget(self.export_pdf_btn)
        
        button_layout.addStretch()
        central_layout.addLayout(button_layout)
        
        # Left dock widget for track panel
        track_dock = QDockWidget("Data Files", self)
        track_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.track_panel = TrackPanel()
        track_dock.setWidget(self.track_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, track_dock)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _connect_signals(self):
        """Connect signals from widgets to handlers."""
        # Navigation bar
        self.nav_bar.region_changed.connect(self._on_region_changed)
        self.nav_bar.gene_region_changed.connect(self._on_region_changed)
        self.nav_bar.zoom_in_clicked.connect(self._on_zoom_in)
        self.nav_bar.zoom_out_clicked.connect(self._on_zoom_out)
        self.nav_bar.pan_left_clicked.connect(self._on_pan_left)
        self.nav_bar.pan_right_clicked.connect(self._on_pan_right)
        
        # Track panel
        self.track_panel.hic_file_selected.connect(self._on_hic_file_selected)
        self.track_panel.track_added.connect(self._on_track_added)
        self.track_panel.track_toggled.connect(self._on_track_toggled)
        self.track_panel.track_removed.connect(self._on_track_removed)
        self.track_panel.track_edit_requested.connect(self._on_track_edit_requested)
        self.track_panel.track_list.track_order_changed.connect(self._on_track_order_changed)
        self.track_panel.norm_combo.currentTextChanged.connect(self._on_normalization_changed)
        self.track_panel.vmin_slider.valueChanged.connect(self._on_vmin_slider_changed)
        self.track_panel.vmax_slider.valueChanged.connect(self._on_vmax_slider_changed)
        self.track_panel.auto_vmin_check.toggled.connect(self._on_auto_vmin_toggled)
        self.track_panel.auto_vmax_check.toggled.connect(self._on_auto_vmax_toggled)
        self.track_panel.auto_resolution_check.toggled.connect(self._on_auto_resolution_toggled)
        self.track_panel.resolution_spin.valueChanged.connect(self._on_resolution_changed)
        self.track_panel.cmap_combo.currentTextChanged.connect(self._on_cmap_changed)
        self.track_panel.show_colorbar_check.toggled.connect(self._on_show_colorbar_toggled)
        
        # Navigation bar chromosome selection
        self.nav_bar.chrom_combo.currentTextChanged.connect(self._on_chromosome_changed)
        
        # Control buttons
        self.preview_btn.clicked.connect(self._on_preview)
        self.export_png_btn.clicked.connect(self._on_export_png)
        self.export_pdf_btn.clicked.connect(self._on_export_pdf)
    
    # Navigation handlers
    
    def _on_region_changed(self, chrom: str, start: int, end: int):
        """Handle region change from navigation bar."""
        self.viewer_state.set_region(chrom, start, end)
        self.nav_bar.set_region(chrom, start, end)
        self._update_resolution_if_auto()
        self.status_bar.showMessage(f"Region: {self.viewer_state.region_string()}")
    
    def _update_resolution_if_auto(self) -> None:
        """Update resolution automatically based on region size if auto mode is enabled."""
        if not self.viewer_state.auto_resolution or not self.viewer_state.available_resolutions:
            return
        
        region_size = self.viewer_state.region_size
        
        # Select resolution based on region size
        # For very large regions (>100Mb), use max resolution
        # For smaller regions, use smaller resolution
        if region_size > 100_000_000:
            # Use maximum resolution for large regions
            selected_resolution = max(self.viewer_state.available_resolutions)
        else:
            # Choose resolution based on region size
            # Aim for ~1000-5000 bins in the region
            target_bins = 2000
            ideal_resolution = region_size // target_bins
            
            # Find the closest available resolution
            selected_resolution = min(
                self.viewer_state.available_resolutions,
                key=lambda x: abs(x - ideal_resolution)
            )
            
            # Ensure we don't use resolution larger than region size
            if selected_resolution > region_size:
                selected_resolution = min(
                    [r for r in self.viewer_state.available_resolutions if r <= region_size],
                    default=max(self.viewer_state.available_resolutions)
                )
        
        if selected_resolution != self.viewer_state.resolution:
            self.viewer_state.resolution = selected_resolution
            # Update spinbox display (it's disabled in auto mode, so won't trigger signal)
            self.track_panel.set_resolution(selected_resolution)
            self.status_bar.showMessage(f"Auto resolution: {selected_resolution:,} bp")
    
    def _on_auto_resolution_toggled(self, enabled: bool):
        """Handle auto resolution checkbox toggle."""
        self.viewer_state.auto_resolution = enabled
        if enabled:
            self._update_resolution_if_auto()
            self.status_bar.showMessage("Auto resolution enabled")
        else:
            self.status_bar.showMessage("Auto resolution disabled")
    
    def _on_resolution_changed(self, value: int):
        """Handle manual resolution change (when auto is disabled)."""
        if not self.viewer_state.auto_resolution:
            self.viewer_state.resolution = value
            self.status_bar.showMessage(f"Resolution set to: {value:,} bp")
    
    def _on_chromosome_changed(self, chrom: str):
        """Handle chromosome selection change."""
        # Update viewer_state chrom but keep current region
        self.viewer_state.chrom = chrom
        # Auto-update resolution for new chromosome if auto resolution is enabled
        if hasattr(self, '_update_resolution_if_auto'):
            self._update_resolution_if_auto()
    
    def _on_normalization_changed(self, norm: str):
        """Handle normalization method change."""
        self.viewer_state.normalization = norm
        self.status_bar.showMessage(f"Normalization changed to: {norm}")
    
    def _on_cmap_changed(self, cmap: str):
        """Handle colormap change."""
        self.viewer_state.cmap = cmap
        self.status_bar.showMessage(f"Colormap changed to: {cmap}")
    
    def _on_show_colorbar_toggled(self, enabled: bool):
        """Handle show colorbar checkbox toggle."""
        self.viewer_state.show_colorbar = enabled
        self.status_bar.showMessage(f"Colorbar: {'shown' if enabled else 'hidden'}")
    
    def _on_vmin_slider_changed(self, value: int):
        """Handle vmin slider value change."""
        if not self.track_panel.auto_vmin_check.isChecked():
            # Convert slider value to actual vmin using stored range
            actual_min, actual_max = self.track_panel._actual_vmin_range
            vmin = actual_min + (actual_max - actual_min) * (value / 1000.0)
            self.viewer_state.vmin = vmin
            self.track_panel.vmin_display_label.setText(f"(current: {vmin:.2f})")
            self.status_bar.showMessage(f"Min value set to: {vmin:.2f}")
    
    def _on_vmax_slider_changed(self, value: int):
        """Handle vmax slider value change."""
        if not self.track_panel.auto_vmax_check.isChecked():
            # Convert slider value to actual vmax using stored range
            actual_min, actual_max = self.track_panel._actual_vmax_range
            vmax = actual_min + (actual_max - actual_min) * (value / 1000.0)
            self.viewer_state.vmax = vmax
            self.track_panel.vmax_display_label.setText(f"(current: {vmax:.2f})")
            self.status_bar.showMessage(f"Max value set to: {vmax:.2f}")
    
    def _on_auto_vmin_toggled(self, enabled: bool):
        """Handle auto vmin checkbox toggle."""
        if enabled:
            self.viewer_state.vmin = None
            self.status_bar.showMessage("Min value: Auto")
        else:
            self.viewer_state.vmin = self.track_panel.vmin_spin.value()
            self.status_bar.showMessage(f"Min value: {self.viewer_state.vmin:.2f}")
    
    def _on_auto_vmax_toggled(self, enabled: bool):
        """Handle auto vmax checkbox toggle."""
        if enabled:
            self.viewer_state.vmax = None
            self.status_bar.showMessage("Max value: Auto")
        else:
            self.viewer_state.vmax = self.track_panel.vmax_spin.value()
            self.status_bar.showMessage(f"Max value: {self.viewer_state.vmax:.2f}")
    
    def _on_zoom_in(self):
        """Handle zoom in button click."""
        self.viewer_state.zoom(2.0)  # Zoom in 2x
        self.nav_bar.set_region(
            self.viewer_state.chrom,
            self.viewer_state.start,
            self.viewer_state.end
        )
        self._update_resolution_if_auto()
        self.status_bar.showMessage(f"Zoomed in: {self.viewer_state.region_string()}")
    
    def _on_zoom_out(self):
        """Handle zoom out button click."""
        self.viewer_state.zoom(0.5)  # Zoom out 2x
        self.nav_bar.set_region(
            self.viewer_state.chrom,
            self.viewer_state.start,
            self.viewer_state.end
        )
        self._update_resolution_if_auto()
        self.status_bar.showMessage(f"Zoomed out: {self.viewer_state.region_string()}")
    
    def _on_pan_left(self):
        """Handle pan left button click."""
        pan_distance = -int(self.viewer_state.region_size * 0.25)  # Pan 25% left
        self.viewer_state.pan(pan_distance)
        self.nav_bar.set_region(
            self.viewer_state.chrom,
            self.viewer_state.start,
            self.viewer_state.end
        )
        self._update_resolution_if_auto()
        self.status_bar.showMessage(f"Panned left: {self.viewer_state.region_string()}")
    
    def _on_pan_right(self):
        """Handle pan right button click."""
        pan_distance = int(self.viewer_state.region_size * 0.25)  # Pan 25% right
        self.viewer_state.pan(pan_distance)
        self.nav_bar.set_region(
            self.viewer_state.chrom,
            self.viewer_state.start,
            self.viewer_state.end
        )
        self._update_resolution_if_auto()
        self.status_bar.showMessage(f"Panned right: {self.viewer_state.region_string()}")
    
    # Track management handlers
    
    def _on_hic_file_selected(self, filepath: str):
        """Handle Hi-C file selection; load in background so UI stays responsive."""
        if self._hic_load_worker is not None and self._hic_load_worker.isRunning():
            self.status_bar.showMessage("Already loading a file, please wait.")
            return
        self.viewer_state.hic_file = filepath
        self.status_bar.showMessage("Loading Hi-C file…")
        self._hic_load_worker = LoadHiCWorker(filepath)
        self._hic_load_worker.finished.connect(self._on_hic_load_finished)
        self._hic_load_worker.start()

    def _on_hic_load_finished(self, result_error_tuple):
        """Called from main thread when LoadHiCWorker finishes."""
        result, error = result_error_tuple
        self._hic_load_worker = None
        if error is not None:
            self.status_bar.showMessage(f"Error loading Hi-C file: {error}")
            QMessageBox.critical(
                self,
                "Error Loading Hi-C File",
                f"Failed to load Hi-C file:\n{error}",
            )
            return
        try:
            filepath = result["filepath"]
            matrix_provider = result["matrix_provider"]
            resolutions = result["resolutions"]
            chromosomes = result["chromosomes"]
            default_resolution = result["default_resolution"]
            target_chrom = result["target_chrom"]
            region_start = result["region_start"]
            region_end = result["region_end"]

            # Store provider in data_manager (main thread) for later use
            cache_key = (
                f"{filepath}:{matrix_provider.resolution}"
                if getattr(matrix_provider, "resolution", None) is not None
                else filepath
            )
            self.data_manager._matrix_providers[cache_key] = matrix_provider

            self.viewer_state.available_resolutions = resolutions
            self.viewer_state.resolution = default_resolution
            self.track_panel.set_resolution(default_resolution)
            self.viewer_state.normalization = "NONE"
            self.track_panel.set_normalization("NONE")

            if chromosomes:
                self.nav_bar.update_chromosomes(chromosomes)
                self.viewer_state.set_region(target_chrom, region_start, region_end)
                self.nav_bar.chrom_combo.setCurrentText(target_chrom)
                self.nav_bar.set_region(target_chrom, region_start, region_end)

            self.status_bar.showMessage(f"Loaded Hi-C: {Path(filepath).name}")
            self._on_preview()
        except Exception as e:
            self.status_bar.showMessage(f"Error applying Hi-C data: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to apply loaded data:\n{str(e)}",
            )
    
    def _on_track_added(self, track_type: str, filepath: str):
        """Handle track addition."""
        # Default options based on track type
        default_options = {
            'bigwig': {'color': '#1a5276', 'alpha': 0.8, 'style': 'fill', 'height': 1.0, 'ylim': None},
            'bed': {'color': '#8B1538', 'alpha': 0.85, 'style': 'box', 'height': 0.5},
            'bedpe': {'color': '#0d1b2a', 'alpha': 0.75, 'style': 'arc', 'height': 1.2, 'max_arcs': 500},
            'gene': {'gene_color': '#0d1b2a', 'exon_color': '#1a5276', 'height': 1.5, 'show_gene_names': True, 'max_genes': 10}
        }
        
        track_config = TrackConfig(
            track_type=track_type,
            filepath=filepath,
            visible=True,
            options=default_options.get(track_type, {})
        )
        
        self.viewer_state.add_track(track_config)
        # Update track list display
        self._update_track_list_display()
        self.status_bar.showMessage(f"Added {track_type} track: {filepath}")
    
    def _update_track_list_display(self):
        """Update track list widget to reflect current tracks."""
        self.track_panel.track_list.clear()
        for i, track_config in enumerate(self.viewer_state.tracks):
            display_name = track_config.name or Path(track_config.filepath).stem
            item_text = f"[{track_config.track_type}] {display_name}"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if track_config.visible else Qt.Unchecked)
            item.setData(Qt.UserRole, i)  # Store index
            self.track_panel.track_list.addItem(item)
    
    def _on_track_edit_requested(self, index: int):
        """Handle track edit request."""
        if 0 <= index < len(self.viewer_state.tracks):
            track_config = self.viewer_state.tracks[index]
            dialog = TrackPropertiesDialog(track_config, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                values = dialog.get_values()
                
                # Update track configuration
                if 'name' in values:
                    track_config.name = values['name']
                
                # Update all options from dialog
                for key, value in values.items():
                    if key != 'name':
                        track_config.options[key] = value
                
                # Update display
                self._update_track_list_display()
                self.status_bar.showMessage(f"Updated {track_config.track_type} track properties")
    
    def _on_track_toggled(self, item: QListWidgetItem):
        """Handle track visibility toggle."""
        # Get index from item data
        track_index = item.data(Qt.UserRole)
        if track_index is not None and 0 <= track_index < len(self.viewer_state.tracks):
            self.viewer_state.toggle_track_visibility(track_index)
            self.status_bar.showMessage(f"Toggled track {track_index} visibility")
    
    def _on_track_removed(self):
        """Handle track removal."""
        current_row = self.track_panel.track_list.currentRow()
        if current_row >= 0:
            item = self.track_panel.track_list.item(current_row)
            if item:
                track_index = item.data(Qt.UserRole)
                if track_index is not None and 0 <= track_index < len(self.viewer_state.tracks):
                    self.viewer_state.remove_track(track_index)
                    self._update_track_list_display()
                    self.status_bar.showMessage(f"Removed track {track_index}")

    def _on_track_order_changed(self, new_order: list):
        """Apply new track order from drag-drop in list."""
        if not new_order or len(new_order) != len(self.viewer_state.tracks):
            return
        # Reorder state to match list widget order
        self.viewer_state.tracks = [self.viewer_state.tracks[i] for i in new_order]
        self._update_track_list_display()
        self.status_bar.showMessage("Track order updated")
    
    # Rendering and export handlers
    
    def _on_preview(self):
        """Handle preview button click - render current view."""
        try:
            self.status_bar.showMessage("Rendering...")
            self.canvas.clear()
            
            # Update viewer_state with current UI values
            self.viewer_state.vmin = self.track_panel.get_vmin()
            self.viewer_state.vmax = self.track_panel.get_vmax()
            # Use canvas width so plot resizes with window (preview uses dpi=100 in controller)
            w_px = max(100, self.canvas.size().width())
            self.viewer_state.figure_width = w_px / 100.0
            figure = self.canvas.get_figure()
            self.render_controller.render(self.viewer_state, figure, preview=True)
            
            # Update vmin/vmax display with actual values used
            if hasattr(self.viewer_state, '_last_hic_track') and self.viewer_state._last_hic_track:
                hic_track = self.viewer_state._last_hic_track
                # Show actual value used (from track) if auto, or user's value if manual
                if hic_track.actual_vmin is not None and hic_track.actual_vmax is not None:
                    # Update display and slider range with actual data range
                    actual_min = hic_track.actual_vmin
                    actual_max = hic_track.actual_vmax
                    actual_range = (actual_min, actual_max)
                    
                    if self.viewer_state.vmin is None:
                        display_vmin = actual_min
                    else:
                        display_vmin = self.viewer_state.vmin
                    self.track_panel.update_vmin_display(display_vmin, actual_range)
                    
                    if self.viewer_state.vmax is None:
                        display_vmax = actual_max
                    else:
                        display_vmax = self.viewer_state.vmax
                    self.track_panel.update_vmax_display(display_vmax, actual_range)
            
            self.canvas.refresh()
            self.status_bar.showMessage(
                f"Preview rendered: {self.viewer_state.region_string()}"
            )
        
        except Exception as e:
            self.status_bar.showMessage(f"Error rendering: {e}")
            QMessageBox.critical(
                self,
                "Rendering Error",
                f"Failed to render view:\n{str(e)}"
            )
    
    def _on_export_png(self):
        """Handle export PNG button click."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export PNG",
            f"hiceebox_{self.viewer_state.chrom}_{self.viewer_state.start}_{self.viewer_state.end}.png",
            "PNG Files (*.png);;All Files (*)"
        )
        
        if filepath:
            try:
                self.canvas.get_figure().savefig(filepath, dpi=300, bbox_inches='tight')
                self.status_bar.showMessage(f"Exported to: {filepath}")
                QMessageBox.information(self, "Export Successful", f"Saved to:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")
    
    def _on_export_pdf(self):
        """Handle export PDF button click."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF",
            f"hiceebox_{self.viewer_state.chrom}_{self.viewer_state.start}_{self.viewer_state.end}.pdf",
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if filepath:
            try:
                self.canvas.get_figure().savefig(filepath, format='pdf', bbox_inches='tight')
                self.status_bar.showMessage(f"Exported to: {filepath}")
                QMessageBox.information(self, "Export Successful", f"Saved to:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")

