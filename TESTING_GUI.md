# GUI testing guide

## Quick start

### Method 1: Command line (recommended)

```bash
# Make sure you are in the project root
cd /Users/zchen6/Documents/Shenlab/zoechen0717/HiCeeBox

# If not yet installed, install dependencies first
pip install -e .
pip install PySide6 hic-straw cooler pyBigWig pandas

# Run the GUI
hiceebox-gui
```

### Method 2: Run Python module directly

```bash
python -m hiceebox_gui.app
```

### Method 3: Run from Python code

```python
from hiceebox_gui.app import main
main()
```

---

## Feature checklist

### ✅ 1. Basic functionality

#### 1.1 Load Hi-C file
- [ ] Click the "Load .hic or .mcool" button
- [ ] Select a `.hic` or `.mcool` file
- [ ] Confirm the file loads successfully and the status bar shows the filename
- [ ] Confirm the chromosome dropdown updates
- [ ] Confirm the initial region is set correctly

#### 1.2 Navigation
- [ ] Enter coordinates in the "Region" box (e.g. `chr1:1,000,000-2,000,000`)
- [ ] Click the "Go" button and confirm the region updates
- [ ] Test the "Zoom In (+)" button
- [ ] Test the "Zoom Out (−)" button
- [ ] Test the "Pan Left ◄" button
- [ ] Test the "Pan Right ►" button
- [ ] Select different chromosomes from the dropdown

#### 1.3 Preview and export
- [ ] Click the "🔍 Preview" button and confirm the plot renders
- [ ] Click the "💾 Export PNG" button to save a PNG file
- [ ] Click the "📄 Export PDF" button to save a PDF file
- [ ] Open the exported file and confirm image quality

---

### ✅ 2. Hi-C track options

#### 2.1 Resolution
- [ ] Confirm the "Auto" checkbox is checked by default
- [ ] Uncheck "Auto" and set resolution manually
- [ ] Change the resolution value, click Preview, and confirm the plot updates
- [ ] Re-check "Auto" and confirm resolution updates automatically

#### 2.2 Normalization
- [ ] Select "KR" from the dropdown
- [ ] Select "VC"
- [ ] Select "NONE"
- [ ] Click Preview after each change and confirm the plot updates

#### 2.3 Min/Max value (color range)
- [ ] Confirm the "Auto" checkboxes are checked by default
- [ ] Uncheck "Auto" and use the sliders to set Min Value
- [ ] Use the slider to set Max Value
- [ ] Confirm the status bar shows the current values
- [ ] Click Preview and confirm the color range changes

#### 2.4 Colormap
- [ ] Select different options from the "Colormap" dropdown:
  - OrRd, Reds, YlOrRd, YlGnBu, viridis, plasma, inferno, magma, coolwarm
- [ ] Click Preview after each change and confirm colors update

#### 2.5 Show colorbar
- [ ] Check the "Show Colorbar" checkbox
- [ ] Click Preview and confirm the colorbar appears
- [ ] Uncheck it and confirm the colorbar is hidden

---

### ✅ 3. Gene name navigation

#### 3.1 Load promoter BED file
- [ ] Click the "Load BED" button (next to the Gene input)
- [ ] Select a promoter BED file (e.g. `hg38.genecode.promoter.selected.2k5bp.bed`)
- [ ] Confirm the filename appears next to the "Promoter BED:" label

#### 3.2 Navigate by gene name
- [ ] Enter a gene name in the "Gene:" box (e.g. `MYC`)
- [ ] Click the "Go (Gene)" button
- [ ] Confirm the region updates to that gene’s location
- [ ] Confirm the navigation bar Region box and chromosome dropdown update

#### 3.3 Error handling
- [ ] Click "Go (Gene)" with no gene name and confirm a warning appears
- [ ] Click "Go (Gene)" without loading a BED file and confirm a warning
- [ ] Enter a non-existent gene name and confirm an error message

---

### ✅ 4. Annotation tracks

#### 4.1 Add BigWig track
- [ ] Click the "Add BigWig" button
- [ ] Select a `.bw` or `.bigwig` file
- [ ] Confirm the track appears in the list
- [ ] Double-click the track or click "Edit Selected" to open properties
- [ ] Test: Track Name, Color, Y Min (Auto/manual), Y Max (Auto/manual), Show Y-axis Labels
- [ ] Click Preview and confirm the track is shown

#### 4.2 Add BED track
- [ ] Click the "Add BED" button
- [ ] Select a `.bed` file
- [ ] Confirm the track appears in the list
- [ ] Click Preview and confirm the track is shown

#### 4.3 Add BEDPE track
- [ ] Click the "Add BEDPE" button
- [ ] Select a `.bedpe` file
- [ ] Confirm the track appears in the list
- [ ] Double-click to open properties and test **Invert Arcs**:
  - [ ] Check "Invert Arcs (Draw Downward)"
  - [ ] Click Preview and confirm arcs are drawn downward
  - [ ] Uncheck and confirm arcs are drawn upward

#### 4.4 Add gene track
- [ ] Click the "Add Genes (GTF/BED12)" button
- [ ] Select a `.gtf`, `.gtf.gz`, or `.bed12` file
- [ ] Confirm the track appears in the list
- [ ] Double-click to open properties and test:
  - [ ] **Query Gene** (e.g. `MYC`)
  - [ ] **Layout Mode**: "expanded" (multi-row) and "condensed" (single-row)
- [ ] Click Preview and confirm genes are shown
- [ ] If Query Gene is set, confirm that gene is always shown

#### 4.5 Track management
- [ ] Use the track list checkboxes to show/hide tracks
- [ ] Select a track and click "Remove Selected" to delete
- [ ] Confirm the track is removed from the list after deletion

---

### ✅ 5. Integration test scenarios

#### Scenario 1: Full example
1. Load a Hi-C file
2. Navigate by gene name to `MYC`
3. Add: Hi-C (e.g. colormap='Reds', show_colorbar=False), BigWig (e.g. ylim=(0, 100), show_ylim_labels=True), BED, BEDPE (invert=True), Gene (query_gene='MYC', layout_mode='expanded')
4. Click Preview and confirm all tracks display correctly
5. Export as PDF

#### Scenario 2: Interactive exploration
1. Load a Hi-C file
2. Use Zoom In/Out and Pan Left/Right to explore regions
3. Change resolution, normalization, and color range
4. Add/remove tracks and observe plot updates
5. Try different colormap options

#### Scenario 3: Performance
1. Load a large Hi-C file (>100MB)
2. Add several tracks (5+)
3. Test render speed at different resolutions
4. Test export performance for large figures

---

## Troubleshooting

### Issue 1: GUI does not start
```bash
# Check dependencies
python -c "import PySide6; print('PySide6 OK')"
python -c "from hiceebox_gui.app import main; print('Module OK')"
```

### Issue 2: Hi-C file fails to load
- Confirm the file is `.hic` or `.mcool`
- Check the file path
- Check the terminal for error messages

### Issue 3: Track does not show
- Check the file path
- Confirm the file format matches the track type
- Check the status bar for errors

### Issue 4: Gene name navigation fails
- Confirm the promoter BED has at least 4 columns: chrom, start, end, name
- Confirm the gene name exists in the BED file
- Check the name_column setting (default is column 6)

---

## Test report template

```
Test date: [date]
Tester: [name]
Python version: [version]
OS: [system]

Basic functionality: ✅ / ❌
Hi-C options: ✅ / ❌
Gene navigation: ✅ / ❌
Track management: ✅ / ❌
Export: ✅ / ❌

Issues:
1. [description]
2. [description]

Suggestions:
1. [suggestion]
2. [suggestion]
```

---

## Quick test commands

```bash
cd /path/to/HiCeeBox
hiceebox-gui
# or
python -m hiceebox_gui.app
```

---

Use example data when available; test one feature at a time. Watch the status bar for errors.
