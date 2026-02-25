# HiCeeBox

Interactive genome browser for Hi-C contact maps and other tracks (BigWig, BED, BEDPE, genes). Use the GUI app or the Python API.

**Quick run (GUI):** `pip install -e .` then `hiceebox-gui` (requires PySide6, hic-straw, cooler, pyBigWig for full features).

**macOS app:** See `QUICKSTART_MAC.md` for building a standalone `.app` / DMG. After `./build_macos.sh` you get `HiCeeBox-0.1.0.dmg` to share; recipients only need macOS, no Python.

**Python API:**

```bash
pip install -e .
pip install hic-straw cooler pyBigWig  # for Hi-C and bigwig
```

```python
from hiceebox.view import GenomeView
from hiceebox.matrix import HicMatrixProvider
from hiceebox.tracks import HiCTriangleTrack, BigWigTrack, GeneTrack

view = GenomeView(chrom='chr1', start=1_000_000, end=2_000_000)
view.add_track(HiCTriangleTrack(matrix_provider=HicMatrixProvider('data.hic'), resolution=10000))
view.add_track(BigWigTrack('signal.bw'))
view.add_track(GeneTrack('genes.gtf.gz'))
view.plot(output='figure.pdf')
```

- **Code:** `hiceebox/` (core), `hiceebox_gui/` (GUI)
- **Examples:** `examples/HiCeeBox_Tutorial.ipynb`, `examples/HiCeeBox_Demo.ipynb`
- **Build:** `HiCeeBox.spec`, `build_macos.sh` (PyInstaller); optional icon in `assets/` (see `assets/README.md`)

Python 3.10+. License: MIT.
