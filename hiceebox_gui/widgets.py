"""
Custom Qt widgets for HiCeeBox GUI.

Includes file panels, track selectors, and navigation controls.
"""

import sys
from typing import Optional, Callable, List
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QCheckBox, QFileDialog, QGroupBox, QSpinBox, QSlider, QDoubleSpinBox,
    QDialog, QDialogButtonBox, QColorDialog, QMessageBox,
    QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


class TrackListWidget(QListWidget):
    """List widget for tracks; supports drag-drop reorder and emits new order when dropped."""
    track_order_changed = Signal(list)  # list of original indices in new order

    def dropEvent(self, event):
        super().dropEvent(event)
        order = []
        for r in range(self.count()):
            item = self.item(r)
            if item is not None:
                idx = item.data(Qt.UserRole)
                if idx is not None:
                    order.append(int(idx))
        if order:
            self.track_order_changed.emit(order)


class NavigationBar(QWidget):
    """
    Top navigation bar with chromosome selector, coordinate input, and zoom/pan controls.
    """
    
    # Signals
    region_changed = Signal(str, int, int)  # chrom, start, end
    gene_region_changed = Signal(str, int, int)  # chrom, start, end (from gene)
    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    pan_left_clicked = Signal()
    pan_right_clicked = Signal()
    
    def __init__(self, parent=None):
        """Initialize navigation bar."""
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI layout (two rows so the bar is not too long)."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)
        
        # Default promoter.bed: in dev use project root; in frozen app use bundle resource dir
        self.promoter_bed_path = None
        if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
            _default_promoter = Path(sys._MEIPASS) / "promoter.bed"
        else:
            _default_promoter = Path(__file__).resolve().parent.parent / "promoter.bed"
        if _default_promoter.exists():
            self.promoter_bed_path = str(_default_promoter)
        
        # Row 1: Region (chrom, coords, Go) + Gene (gene name, promoter BED, Load, Go Gene)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Chromosome:"))
        self.chrom_combo = QComboBox()
        self.chrom_combo.addItems([f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY", "chrM"])
        self.chrom_combo.setCurrentText("chr1")
        row1.addWidget(self.chrom_combo)
        row1.addWidget(QLabel("Region:"))
        self.region_input = QLineEdit()
        self.region_input.setPlaceholderText("chr1:1,000,000-2,000,000")
        self.region_input.setMinimumWidth(200)
        row1.addWidget(self.region_input)
        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self._on_go_clicked)
        row1.addWidget(self.go_button)
        row1.addSpacing(12)
        row1.addWidget(QLabel("Gene:"))
        self.gene_input = QLineEdit()
        self.gene_input.setPlaceholderText("MYC")
        self.gene_input.setMinimumWidth(80)
        row1.addWidget(self.gene_input)
        row1.addWidget(QLabel("Promoter BED:"))
        self.promoter_bed_label = QLabel("Not set")
        self.promoter_bed_label.setStyleSheet("color: gray;")
        self.promoter_bed_label.setMinimumWidth(80)
        row1.addWidget(self.promoter_bed_label)
        self.load_promoter_btn = QPushButton("Load BED")
        self.load_promoter_btn.clicked.connect(self._load_promoter_bed)
        row1.addWidget(self.load_promoter_btn)
        self.gene_go_button = QPushButton("Go (Gene)")
        self.gene_go_button.clicked.connect(self._on_gene_go_clicked)
        row1.addWidget(self.gene_go_button)
        row1.addStretch()
        main_layout.addLayout(row1)
        
        if _default_promoter.exists():
            self.promoter_bed_label.setText(_default_promoter.name)
            self.promoter_bed_label.setStyleSheet("color: black;")
        
        # Row 2: Pan and Zoom
        row2 = QHBoxLayout()
        self.pan_left_btn = QPushButton("◄ Pan Left")
        self.pan_left_btn.clicked.connect(self.pan_left_clicked.emit)
        row2.addWidget(self.pan_left_btn)
        self.pan_right_btn = QPushButton("Pan Right ►")
        self.pan_right_btn.clicked.connect(self.pan_right_clicked.emit)
        row2.addWidget(self.pan_right_btn)
        row2.addSpacing(12)
        self.zoom_in_btn = QPushButton("Zoom In (+)")
        self.zoom_in_btn.clicked.connect(self.zoom_in_clicked.emit)
        row2.addWidget(self.zoom_in_btn)
        self.zoom_out_btn = QPushButton("Zoom Out (−)")
        self.zoom_out_btn.clicked.connect(self.zoom_out_clicked.emit)
        row2.addWidget(self.zoom_out_btn)
        row2.addStretch()
        main_layout.addLayout(row2)
    
    def _on_go_clicked(self):
        """Handle Go button click - parse region string."""
        region_str = self.region_input.text().strip()
        if not region_str:
            return
        
        try:
            # Parse region string: chr1:1000000-2000000 or chr1:1,000,000-2,000,000
            if ':' in region_str and '-' in region_str:
                chrom, coords = region_str.split(':')
                start_str, end_str = coords.split('-')
                
                # Remove commas
                start = int(start_str.replace(',', ''))
                end = int(end_str.replace(',', ''))
                
                self.region_changed.emit(chrom, start, end)
            else:
                print(f"Invalid region format: {region_str}")
        except Exception as e:
            print(f"Error parsing region: {e}")
    
    def set_region(self, chrom: str, start: int, end: int):
        """
        Update the displayed region.
        
        Args:
            chrom: Chromosome name
            start: Start position
            end: End position
        """
        self.chrom_combo.setCurrentText(chrom)
        self.region_input.setText(f"{chrom}:{start:,}-{end:,}")
    
    def _load_promoter_bed(self):
        """Open file dialog to load promoter BED file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Promoter BED File",
            "",
            "BED Files (*.bed);;All Files (*)"
        )
        
        if filepath:
            self.promoter_bed_path = filepath
            self.promoter_bed_label.setText(Path(filepath).name)
            self.promoter_bed_label.setStyleSheet("color: black;")
    
    def _on_gene_go_clicked(self):
        """Handle Gene Go button click - locate region by gene name."""
        gene_name = self.gene_input.text().strip()
        if not gene_name:
            QMessageBox.warning(self, "No Gene Name", "Please enter a gene name.")
            return
        
        if not self.promoter_bed_path:
            QMessageBox.warning(self, "No Promoter BED", "Please load a promoter BED file first.")
            return
        
        try:
            from hiceebox.utils.genomics import region_from_gene_promoter
            chrom, start, end = region_from_gene_promoter(
                gene_name,
                self.promoter_bed_path,
                upstream=500000,
                downstream=500000,
                name_column=6
            )
            self.gene_region_changed.emit(chrom, start, end)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to locate gene '{gene_name}':\n{str(e)}"
            )
    
    def update_chromosomes(self, chromosomes: List[str]) -> None:
        """
        Update chromosome dropdown with available chromosomes.
        
        Args:
            chromosomes: List of chromosome names from the loaded file
        """
        current = self.chrom_combo.currentText()
        self.chrom_combo.clear()
        self.chrom_combo.addItem("all")
        self.chrom_combo.addItems(chromosomes)
        # Try to restore selection, or default to first chromosome
        index = self.chrom_combo.findText(current)
        if index >= 0:
            self.chrom_combo.setCurrentIndex(index)
        elif chromosomes:
            self.chrom_combo.setCurrentText(chromosomes[0])


class TrackPanel(QWidget):
    """
    Left side panel for managing tracks.
    """
    
    # Signals
    hic_file_selected = Signal(str)  # filepath
    track_added = Signal(str, str)  # track_type, filepath
    track_toggled = Signal(object)  # QListWidgetItem
    track_removed = Signal()  # No args - will get from current selection
    track_edit_requested = Signal(int)  # index
    
    def __init__(self, parent=None):
        """Initialize track panel."""
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        
        # Hi-C file selection
        hic_group = QGroupBox("Hi-C Matrix")
        hic_layout = QVBoxLayout(hic_group)
        
        self.hic_label = QLabel("No file loaded")
        self.hic_label.setWordWrap(True)
        hic_layout.addWidget(self.hic_label)
        
        hic_btn = QPushButton("Load .hic or .mcool")
        hic_btn.clicked.connect(self._load_hic_file)
        hic_layout.addWidget(hic_btn)
        
        # Resolution selector with Auto option
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Resolution (bp):"))
        self.auto_resolution_check = QCheckBox("Auto")
        self.auto_resolution_check.setChecked(True)  # Default to auto
        res_layout.addWidget(self.auto_resolution_check)
        self.resolution_spin = QSpinBox()
        self.resolution_spin.setRange(1000, 1000000)
        self.resolution_spin.setValue(10000)
        self.resolution_spin.setSingleStep(5000)
        self.resolution_spin.setEnabled(False)  # Disabled when auto is on
        res_layout.addWidget(self.resolution_spin)
        # Connect checkbox to enable/disable spinbox
        self.auto_resolution_check.toggled.connect(self.resolution_spin.setDisabled)
        hic_layout.addLayout(res_layout)
        
        # Normalization selector
        norm_layout = QHBoxLayout()
        norm_layout.addWidget(QLabel("Normalization:"))
        self.norm_combo = QComboBox()
        self.norm_combo.addItems(["KR", "VC", "NONE"])
        self.norm_combo.setCurrentText("KR")
        norm_layout.addWidget(self.norm_combo)
        hic_layout.addLayout(norm_layout)
        
        # Colormap selector
        cmap_layout = QHBoxLayout()
        cmap_layout.addWidget(QLabel("Colormap:"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(["OrRd", "Reds", "YlOrRd", "YlGnBu", "viridis", "plasma", "inferno", "magma", "coolwarm"])
        self.cmap_combo.setCurrentText("OrRd")
        cmap_layout.addWidget(self.cmap_combo)
        hic_layout.addLayout(cmap_layout)
        
        # Show colorbar checkbox
        self.show_colorbar_check = QCheckBox("Show Colorbar")
        self.show_colorbar_check.setChecked(False)
        hic_layout.addWidget(self.show_colorbar_check)
        
        # Vmin/Vmax controls with sliders
        # Store actual data range for slider conversion
        self._actual_vmin_range = (0.0, 10.0)  # Will be updated after rendering
        self._actual_vmax_range = (0.0, 10.0)  # Will be updated after rendering
        
        vmin_layout = QHBoxLayout()
        vmin_layout.addWidget(QLabel("Min Value:"))
        self.auto_vmin_check = QCheckBox("Auto")
        self.auto_vmin_check.setChecked(True)  # Default to auto
        vmin_layout.addWidget(self.auto_vmin_check)
        
        # Label showing min range value
        self.vmin_range_label = QLabel("0.00")
        self.vmin_range_label.setStyleSheet("color: gray; font-size: 8pt;")
        self.vmin_range_label.setMinimumWidth(45)
        self.vmin_range_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vmin_layout.addWidget(self.vmin_range_label)
        
        # Slider for vmin
        self.vmin_slider = QSlider(Qt.Horizontal)
        self.vmin_slider.setRange(0, 1000)  # 0-1000 scale, will be mapped to actual range
        self.vmin_slider.setValue(0)
        self.vmin_slider.setEnabled(False)  # Disabled when auto is on
        self.vmin_slider.setFixedWidth(113)  # 3cm ≈ 113 pixels at 96 DPI
        vmin_layout.addWidget(self.vmin_slider)
        
        # Label showing max range value
        self.vmin_max_range_label = QLabel("10.00")
        self.vmin_max_range_label.setStyleSheet("color: gray; font-size: 8pt;")
        self.vmin_max_range_label.setMinimumWidth(45)
        self.vmin_max_range_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        vmin_layout.addWidget(self.vmin_max_range_label)
        
        # Display label showing current value
        self.vmin_display_label = QLabel("(current: Auto)")
        self.vmin_display_label.setStyleSheet("color: gray; font-size: 9pt;")
        self.vmin_display_label.setMinimumWidth(120)
        vmin_layout.addWidget(self.vmin_display_label)
        
        self.auto_vmin_check.toggled.connect(self.vmin_slider.setDisabled)
        hic_layout.addLayout(vmin_layout)
        
        vmax_layout = QHBoxLayout()
        vmax_layout.addWidget(QLabel("Max Value:"))
        self.auto_vmax_check = QCheckBox("Auto")
        self.auto_vmax_check.setChecked(True)  # Default to auto
        vmax_layout.addWidget(self.auto_vmax_check)
        
        # Label showing min range value
        self.vmax_range_label = QLabel("0.00")
        self.vmax_range_label.setStyleSheet("color: gray; font-size: 8pt;")
        self.vmax_range_label.setMinimumWidth(45)
        self.vmax_range_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vmax_layout.addWidget(self.vmax_range_label)
        
        # Slider for vmax
        self.vmax_slider = QSlider(Qt.Horizontal)
        self.vmax_slider.setRange(0, 1000)  # 0-1000 scale, will be mapped to actual range
        self.vmax_slider.setValue(1000)
        self.vmax_slider.setEnabled(False)  # Disabled when auto is on
        self.vmax_slider.setFixedWidth(113)  # 3cm ≈ 113 pixels at 96 DPI
        vmax_layout.addWidget(self.vmax_slider)
        
        # Label showing max range value
        self.vmax_max_range_label = QLabel("10.00")
        self.vmax_max_range_label.setStyleSheet("color: gray; font-size: 8pt;")
        self.vmax_max_range_label.setMinimumWidth(45)
        self.vmax_max_range_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        vmax_layout.addWidget(self.vmax_max_range_label)
        
        # Display label showing current value
        self.vmax_display_label = QLabel("(current: Auto)")
        self.vmax_display_label.setStyleSheet("color: gray; font-size: 9pt;")
        self.vmax_display_label.setMinimumWidth(120)
        vmax_layout.addWidget(self.vmax_display_label)
        
        self.auto_vmax_check.toggled.connect(self.vmax_slider.setDisabled)
        hic_layout.addLayout(vmax_layout)
        
        layout.addWidget(hic_group)
        
        # Track list
        track_group = QGroupBox("Annotation Tracks")
        track_layout = QVBoxLayout(track_group)
        
        # Add track buttons
        btn_layout = QVBoxLayout()
        
        self.add_bigwig_btn = QPushButton("Add BigWig")
        self.add_bigwig_btn.clicked.connect(lambda: self._add_track('bigwig'))
        btn_layout.addWidget(self.add_bigwig_btn)
        
        self.add_bed_btn = QPushButton("Add BED")
        self.add_bed_btn.clicked.connect(lambda: self._add_track('bed'))
        btn_layout.addWidget(self.add_bed_btn)
        
        self.add_bedpe_btn = QPushButton("Add BEDPE")
        self.add_bedpe_btn.clicked.connect(lambda: self._add_track('bedpe'))
        btn_layout.addWidget(self.add_bedpe_btn)
        
        self.add_gene_btn = QPushButton("Add Genes (GTF/BED12)")
        self.add_gene_btn.clicked.connect(lambda: self._add_track('gene'))
        btn_layout.addWidget(self.add_gene_btn)
        
        track_layout.addLayout(btn_layout)
        
        # Track list (drag-drop reorder enabled)
        self.track_list = TrackListWidget()
        self.track_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.track_list.setDefaultDropAction(Qt.MoveAction)
        self.track_list.setDragEnabled(True)
        self.track_list.setAcceptDrops(True)
        self.track_list.setDropIndicatorShown(True)
        self.track_list.itemChanged.connect(self._on_track_item_changed)
        self.track_list.itemDoubleClicked.connect(self._on_track_double_clicked)
        track_layout.addWidget(self.track_list)
        self._track_list_items = {}  # Map track index to list item for easier updates
        
        # Edit and Remove buttons
        button_layout = QHBoxLayout()
        self.edit_track_btn = QPushButton("Edit Selected")
        self.edit_track_btn.clicked.connect(self._edit_selected_track)
        button_layout.addWidget(self.edit_track_btn)
        
        self.remove_track_btn = QPushButton("Remove Selected")
        self.remove_track_btn.clicked.connect(self._remove_selected_track)
        button_layout.addWidget(self.remove_track_btn)
        track_layout.addLayout(button_layout)
        
        layout.addWidget(track_group)
        layout.addStretch()
    
    def _load_hic_file(self):
        """Open file dialog to load Hi-C file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Hi-C File",
            "",
            "Hi-C Files (*.hic *.mcool *.cool);;All Files (*)"
        )
        
        if filepath:
            self.hic_label.setText(Path(filepath).name)
            self.hic_file_selected.emit(filepath)
    
    def _add_track(self, track_type: str):
        """Open file dialog to add a track."""
        filters = {
            'bigwig': "BigWig Files (*.bw *.bigwig);;All Files (*)",
            'bed': "BED Files (*.bed);;All Files (*)",
            'bedpe': "BEDPE Files (*.bedpe);;All Files (*)",
            'gene': "Gene Files (*.gtf *.gtf.gz *.bed12);;All Files (*)"
        }
        
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {track_type.upper()} File",
            "",
            filters.get(track_type, "All Files (*)")
        )
        
        if filepath:
            self.track_added.emit(track_type, filepath)
    
    def _add_track_item(self, track_type: str, filepath: str):
        """Add a track to the list widget."""
        item = QListWidgetItem(f"[{track_type}] {Path(filepath).name}")
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        item.setData(Qt.UserRole, filepath)
        self.track_list.addItem(item)
    
    def _on_track_item_changed(self, item: QListWidgetItem):
        """Handle track item checkbox change."""
        # Signal should be handled by main_window with the item
        self.track_toggled.emit(item)
    
    def _remove_selected_track(self):
        """Ask main window to remove selected track (list is updated via _update_track_list_display)."""
        current_row = self.track_list.currentRow()
        if current_row >= 0:
            self.track_removed.emit()
    
    def get_resolution(self) -> int:
        """Get current resolution setting."""
        return self.resolution_spin.value()
    
    def set_resolution(self, resolution: int) -> None:
        """Set resolution value."""
        self.resolution_spin.setValue(resolution)
    
    def is_auto_resolution(self) -> bool:
        """Check if auto resolution is enabled."""
        return self.auto_resolution_check.isChecked()
    
    def set_auto_resolution(self, enabled: bool) -> None:
        """Set auto resolution mode."""
        self.auto_resolution_check.setChecked(enabled)
    
    def get_normalization(self) -> str:
        """Get current normalization method."""
        return self.norm_combo.currentText()
    
    def set_normalization(self, norm: str) -> None:
        """Set normalization method."""
        index = self.norm_combo.findText(norm.upper())
        if index >= 0:
            self.norm_combo.setCurrentIndex(index)
    
    def get_vmin(self) -> Optional[float]:
        """Get vmin value (None if Auto)."""
        if self.auto_vmin_check.isChecked():
            return None
        # Convert slider value (0-1000) to actual vmin using stored range
        actual_min, actual_max = self._actual_vmin_range
        return self._slider_to_vmin(self.vmin_slider.value(), actual_min, actual_max)
    
    def set_vmin(self, vmin: Optional[float]) -> None:
        """Set vmin value (None for Auto)."""
        if vmin is None:
            self.auto_vmin_check.setChecked(True)
        else:
            self.auto_vmin_check.setChecked(False)
            # Update slider position based on current range
            actual_min, actual_max = self._actual_vmin_range
            slider_value = self._vmin_to_slider(vmin, actual_min, actual_max)
            self.vmin_slider.setValue(slider_value)
    
    def get_vmax(self) -> Optional[float]:
        """Get vmax value (None if Auto)."""
        if self.auto_vmax_check.isChecked():
            return None
        # Convert slider value (0-1000) to actual vmax using stored range
        actual_min, actual_max = self._actual_vmax_range
        return self._slider_to_vmax(self.vmax_slider.value(), actual_min, actual_max)
    
    def set_vmax(self, vmax: Optional[float]) -> None:
        """Set vmax value (None for Auto)."""
        if vmax is None:
            self.auto_vmax_check.setChecked(True)
        else:
            self.auto_vmax_check.setChecked(False)
            # Update slider position based on current range
            actual_min, actual_max = self._actual_vmax_range
            slider_value = self._vmax_to_slider(vmax, actual_min, actual_max)
            self.vmax_slider.setValue(slider_value)
    
    def _vmin_to_slider(self, vmin: float, actual_min: float, actual_max: float) -> int:
        """Convert vmin value to slider position (0-1000)."""
        if actual_max == actual_min:
            return 0
        normalized = max(0, min(1, (vmin - actual_min) / (actual_max - actual_min)))
        return int(normalized * 1000)
    
    def _slider_to_vmin(self, slider_value: int, actual_min: float, actual_max: float) -> float:
        """Convert slider position (0-1000) to vmin value."""
        normalized = slider_value / 1000.0
        return actual_min + normalized * (actual_max - actual_min)
    
    def _vmax_to_slider(self, vmax: float, actual_min: float, actual_max: float) -> int:
        """Convert vmax value to slider position (0-1000)."""
        if actual_max == actual_min:
            return 1000
        normalized = max(0, min(1, (vmax - actual_min) / (actual_max - actual_min)))
        return int(normalized * 1000)
    
    def _slider_to_vmax(self, slider_value: int, actual_min: float, actual_max: float) -> float:
        """Convert slider position (0-1000) to vmax value."""
        normalized = slider_value / 1000.0
        return actual_min + normalized * (actual_max - actual_min)
    
    def update_vmin_display(self, value: Optional[float], actual_range: Optional[tuple] = None) -> None:
        """Update the display label showing current vmin value and update range."""
        if actual_range:
            self._actual_vmin_range = actual_range
            # Update range labels to show actual min/max
            actual_min, actual_max = actual_range
            self.vmin_range_label.setText(f"{actual_min:.2f}")
            self.vmin_max_range_label.setText(f"{actual_max:.2f}")
        
        if value is None:
            self.vmin_display_label.setText("(current: Auto)")
        else:
            self.vmin_display_label.setText(f"(current: {value:.2f})")
            # Update slider position if manual mode
            if not self.auto_vmin_check.isChecked() and actual_range:
                actual_min, actual_max = actual_range
                slider_value = self._vmin_to_slider(value, actual_min, actual_max)
                self.vmin_slider.blockSignals(True)  # Prevent recursive updates
                self.vmin_slider.setValue(slider_value)
                self.vmin_slider.blockSignals(False)
    
    def update_vmax_display(self, value: Optional[float], actual_range: Optional[tuple] = None) -> None:
        """Update the display label showing current vmax value and update range."""
        if actual_range:
            self._actual_vmax_range = actual_range
            # Update range labels to show actual min/max
            actual_min, actual_max = actual_range
            self.vmax_range_label.setText(f"{actual_min:.2f}")
            self.vmax_max_range_label.setText(f"{actual_max:.2f}")
        
        if value is None:
            self.vmax_display_label.setText("(current: Auto)")
        else:
            self.vmax_display_label.setText(f"(current: {value:.2f})")
            # Update slider position if manual mode
            if not self.auto_vmax_check.isChecked() and actual_range:
                actual_min, actual_max = actual_range
                slider_value = self._vmax_to_slider(value, actual_min, actual_max)
                self.vmax_slider.blockSignals(True)  # Prevent recursive updates
                self.vmax_slider.setValue(slider_value)
                self.vmax_slider.blockSignals(False)
    
    def _edit_selected_track(self):
        """Handle edit button click - open track properties dialog."""
        current_row = self.track_list.currentRow()
        if current_row >= 0:
            self.track_edit_requested.emit(current_row)
    
    def _on_track_double_clicked(self, item: QListWidgetItem):
        """Handle track double click - same as edit."""
        current_row = self.track_list.row(item)
        if current_row >= 0:
            self.track_edit_requested.emit(current_row)


class TrackPropertiesDialog(QDialog):
    """Dialog for editing track properties."""
    
    def __init__(self, track_config, parent=None):
        super().__init__(parent)
        self.track_config = track_config
        self.setWindowTitle(f"Edit {track_config.track_type} Track Properties")
        self.setModal(True)
        self._setup_ui()
        self._load_current_values()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Track name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Track Name:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Height (all track types)
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height:"))
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.2, 5.0)
        self.height_spin.setSingleStep(0.25)
        self.height_spin.setDecimals(2)
        height_layout.addWidget(self.height_spin)
        layout.addLayout(height_layout)
        
        # Track-specific options
        if self.track_config.track_type == 'bigwig':
            # Color selector
            color_layout = QHBoxLayout()
            color_layout.addWidget(QLabel("Color:"))
            self.color_btn = QPushButton()
            self.color_btn.setFixedWidth(60)
            self.color_btn.clicked.connect(self._choose_color)
            color_layout.addWidget(self.color_btn)
            layout.addLayout(color_layout)
            
            # Y-axis min/max with Auto
            ymin_layout = QHBoxLayout()
            ymin_layout.addWidget(QLabel("Y Min:"))
            self.auto_ymin_check = QCheckBox("Auto")
            self.auto_ymin_check.setChecked(True)
            ymin_layout.addWidget(self.auto_ymin_check)
            self.ymin_spin = QDoubleSpinBox()
            self.ymin_spin.setRange(-1000.0, 1000.0)
            self.ymin_spin.setValue(0.0)
            self.ymin_spin.setDecimals(2)
            self.ymin_spin.setEnabled(False)
            self.auto_ymin_check.toggled.connect(self.ymin_spin.setDisabled)
            ymin_layout.addWidget(self.ymin_spin)
            layout.addLayout(ymin_layout)
            
            ymax_layout = QHBoxLayout()
            ymax_layout.addWidget(QLabel("Y Max:"))
            self.auto_ymax_check = QCheckBox("Auto")
            self.auto_ymax_check.setChecked(True)
            ymax_layout.addWidget(self.auto_ymax_check)
            self.ymax_spin = QDoubleSpinBox()
            self.ymax_spin.setRange(-1000.0, 1000.0)
            self.ymax_spin.setValue(100.0)
            self.ymax_spin.setDecimals(2)
            self.ymax_spin.setEnabled(False)
            self.auto_ymax_check.toggled.connect(self.ymax_spin.setDisabled)
            ymax_layout.addWidget(self.ymax_spin)
            layout.addLayout(ymax_layout)
            
            # Show Y-axis labels
            self.show_ylim_labels_check = QCheckBox("Show Y-axis Labels")
            self.show_ylim_labels_check.setChecked(False)
            layout.addWidget(self.show_ylim_labels_check)
        
        elif self.track_config.track_type == 'bedpe':
            # Invert arcs (draw downward)
            self.invert_check = QCheckBox("Invert Arcs (Draw Downward)")
            self.invert_check.setChecked(False)
            layout.addWidget(self.invert_check)
        
        elif self.track_config.track_type == 'gene':
            # Gene name font size
            fontsize_layout = QHBoxLayout()
            fontsize_layout.addWidget(QLabel("Gene name font size:"))
            self.gene_fontsize_spin = QDoubleSpinBox()
            self.gene_fontsize_spin.setRange(4.0, 20.0)
            self.gene_fontsize_spin.setValue(7.0)
            self.gene_fontsize_spin.setSingleStep(0.5)
            self.gene_fontsize_spin.setDecimals(1)
            fontsize_layout.addWidget(self.gene_fontsize_spin)
            layout.addLayout(fontsize_layout)
            
            # Query gene (for ensuring gene is displayed)
            query_gene_layout = QHBoxLayout()
            query_gene_layout.addWidget(QLabel("Query Gene:"))
            self.query_gene_edit = QLineEdit()
            self.query_gene_edit.setPlaceholderText("Leave empty if not using gene-based region")
            query_gene_layout.addWidget(self.query_gene_edit)
            layout.addLayout(query_gene_layout)
            
            # Layout mode
            layout_mode_layout = QHBoxLayout()
            layout_mode_layout.addWidget(QLabel("Layout Mode:"))
            self.layout_mode_combo = QComboBox()
            self.layout_mode_combo.addItems(["expanded", "condensed"])
            self.layout_mode_combo.setCurrentText("expanded")
            layout_mode_layout.addWidget(self.layout_mode_combo)
            layout.addLayout(layout_mode_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_current_values(self):
        """Load current track configuration values."""
        self.name_edit.setText(self.track_config.name or "")
        options = self.track_config.options
        # Height (defaults per type)
        defaults = {'hic': 2.5, 'bigwig': 1.0, 'bed': 0.5, 'bedpe': 1.2, 'gene': 1.5}
        default_h = defaults.get(self.track_config.track_type, 1.0)
        self.height_spin.setValue(float(options.get('height', default_h)))
        
        if self.track_config.track_type == 'bigwig':
            # Load color
            color = options.get('color', '#1a5276')
            self._current_color = QColor(color)
            self._update_color_button()
            
            # Load ylim
            ylim = options.get('ylim', None)
            if ylim is None:
                # Auto mode
                self.auto_ymin_check.setChecked(True)
                self.auto_ymax_check.setChecked(True)
            else:
                ymin, ymax = ylim
                self.auto_ymin_check.setChecked(False)
                self.auto_ymax_check.setChecked(False)
                self.ymin_spin.setValue(ymin)
                self.ymax_spin.setValue(ymax)
            
            # Load show_ylim_labels
            show_ylim_labels = options.get('show_ylim_labels', False)
            self.show_ylim_labels_check.setChecked(show_ylim_labels)
        
        elif self.track_config.track_type == 'bedpe':
            # Load invert
            invert = options.get('invert', False)
            self.invert_check.setChecked(invert)
        
        elif self.track_config.track_type == 'gene':
            # Load gene_fontsize
            self.gene_fontsize_spin.setValue(float(options.get('gene_fontsize', 7.0)))
            # Load query_gene
            query_gene = options.get('query_gene', None)
            if query_gene:
                self.query_gene_edit.setText(query_gene)
            # Load layout_mode
            layout_mode = options.get('layout_mode', 'expanded')
            index = self.layout_mode_combo.findText(layout_mode)
            if index >= 0:
                self.layout_mode_combo.setCurrentIndex(index)
    
    def _choose_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(self._current_color, self, "Choose Track Color")
        if color.isValid():
            self._current_color = color
            self._update_color_button()
    
    def _update_color_button(self):
        """Update color button appearance."""
        self.color_btn.setStyleSheet(f"background-color: {self._current_color.name()};")
        self.color_btn.setText(self._current_color.name())
    
    def get_values(self):
        """Get edited values."""
        name = self.name_edit.text().strip() or None
        result = {'name': name, 'height': self.height_spin.value()}
        
        if self.track_config.track_type == 'bigwig':
            color = self._current_color.name()
            
            if self.auto_ymin_check.isChecked() and self.auto_ymax_check.isChecked():
                ylim = None
            else:
                ymin = self.ymin_spin.value() if not self.auto_ymin_check.isChecked() else None
                ymax = self.ymax_spin.value() if not self.auto_ymax_check.isChecked() else None
                # Always return tuple, even if both are None (will be handled as auto)
                ylim = (ymin, ymax)
            
            result.update({
                'color': color,
                'ylim': ylim,
                'show_ylim_labels': self.show_ylim_labels_check.isChecked()
            })
        
        elif self.track_config.track_type == 'bedpe':
            result['invert'] = self.invert_check.isChecked()
        
        elif self.track_config.track_type == 'gene':
            query_gene = self.query_gene_edit.text().strip() or None
            layout_mode = self.layout_mode_combo.currentText()
            result.update({
                'gene_fontsize': self.gene_fontsize_spin.value(),
                'query_gene': query_gene,
                'layout_mode': layout_mode
            })
        
        return result

