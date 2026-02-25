"""
HiCeeBox: Hi-C + multi-omics visualization toolkit.

A Python package for generating stacked genomic tracks with Hi-C heatmaps
and aligned 1D tracks for multi-omics data visualization.
"""

__version__ = "0.1.0"

from hiceebox.view.genome_view import GenomeView
from hiceebox.matrix.base import MatrixProvider
from hiceebox.tracks.base import Track

__all__ = [
    "GenomeView",
    "MatrixProvider",
    "Track",
]

