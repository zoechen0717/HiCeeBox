# HiCeeBox

Interactive genome browser for Hi-C contact maps and other tracks (BigWig, BED, BEDPE, genes). Python API.

**Install**

```bash
pip install -e .
pip install hic-straw cooler pyBigWig   # for Hi-C and bigwig
```

**Quick example**

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

**Tutorial:** see `examples/HiCeeBox_Tutorial.ipynb` for a walkthrough.

Python 3.10+. MIT.
