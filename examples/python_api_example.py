#!/usr/bin/env python
"""
Example of using HiCeeBox Python API directly.

This script demonstrates how to create multi-track genomic visualizations
programmatically without using YAML configuration files.
"""

from hiceebox import GenomeView
from hiceebox.tracks import (
    HiCTriangleTrack,
    BigWigTrack,
    BedTrack,
    BedPETrack,
    GeneTrack
)
from hiceebox.matrix import HicMatrixProvider, CoolerMatrixProvider


def main():
    """Create a multi-track genomic visualization."""
    
    # Define genomic region
    chrom = 'chr6'
    start = 30_000_000
    end = 32_000_000
    
    # Create GenomeView
    view = GenomeView(
        chrom=chrom,
        start=start,
        end=end,
        width=8,
        dpi=300,
        title=f"Multi-omics View of {chrom}:{start:,}-{end:,}"
    )
    
    # Add Hi-C triangle track
    # For .hic files:
    hic_provider = HicMatrixProvider('data/example.hic')
    # For .mcool files, use:
    # hic_provider = CoolerMatrixProvider('data/example.mcool', resolution=10000)
    
    hic_track = HiCTriangleTrack(
        matrix_provider=hic_provider,
        resolution=10000,
        norm='KR',
        cmap='Reds',
        name='Hi-C',
        height=2.0
    )
    view.add_track(hic_track)
    
    # Add ATAC-seq signal track
    atac_track = BigWigTrack(
        filepath='data/atac.bw',
        name='ATAC-seq',
        color='blue',
        style='fill',
        alpha=0.7,
        height=1.0
    )
    view.add_track(atac_track)
    
    # Add ChIP-seq peaks
    peaks_track = BedTrack(
        filepath='data/peaks.bed',
        name='Peaks',
        color='red',
        alpha=0.7,
        height=0.5
    )
    view.add_track(peaks_track)
    
    # Add chromatin loops
    loops_track = BedPETrack(
        filepath='data/loops.bedpe',
        name='Loops',
        color='black',
        style='arc',
        alpha=0.5,
        height=1.0
    )
    view.add_track(loops_track)
    
    # Add gene annotations
    gene_track = GeneTrack(
        filepath='data/genes.gtf',
        name='Genes',
        gene_color='darkblue',
        exon_color='blue',
        show_gene_names=True,
        max_rows=5,
        height=1.5
    )
    view.add_track(gene_track)
    
    # Generate and save plot
    print(f"Generating plot for {view.region_size:,} bp region...")
    print(f"Total tracks: {len(view.tracks)}")
    
    view.plot(
        output='output_figure.pdf',
        show=False
    )
    
    print("✓ Plot saved to: output_figure.pdf")


if __name__ == '__main__':
    main()

