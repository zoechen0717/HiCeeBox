"""Configuration loader for YAML-based track specifications."""

from typing import Dict, Any
from pathlib import Path
import yaml

from hiceebox.view.genome_view import GenomeView
from hiceebox.tracks.hic_triangle import HiCTriangleTrack
from hiceebox.tracks.bigwig import BigWigTrack
from hiceebox.tracks.bed import BedTrack
from hiceebox.tracks.bedpe import BedPETrack
from hiceebox.tracks.gene import GeneTrack
from hiceebox.matrix.cooler_provider import CoolerMatrixProvider
from hiceebox.matrix.hic_provider import HicMatrixProvider


def load_config(config_path: str) -> GenomeView:
    """
    Load configuration from YAML file and build GenomeView.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configured GenomeView object ready to plot
        
    Example YAML structure:
        region:
          chrom: chr6
          start: 30000000
          end: 32000000
          
        tracks:
          - type: hic_triangle
            file: example.hic
            resolution: 10000
            norm: KR
            cmap: Reds
            
          - type: bigwig
            file: signal.bw
            name: ATAC-seq
            
          - type: gene
            file: genes.gtf
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Load YAML
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    if not config:
        raise ValueError("Empty configuration file")
    
    # Parse region
    region = config.get('region', {})
    chrom = region.get('chrom')
    start = region.get('start')
    end = region.get('end')
    
    if not all([chrom, start, end]):
        raise ValueError("Configuration must specify region with chrom, start, and end")
    
    # Create GenomeView
    view = GenomeView(
        chrom=chrom,
        start=start,
        end=end,
        width=config.get('width', 8.0),
        dpi=config.get('dpi', 300),
        title=config.get('title')
    )
    
    # Parse and add tracks
    tracks = config.get('tracks', [])
    
    for track_config in tracks:
        track = _create_track(track_config)
        view.add_track(track)
    
    return view


def _create_track(track_config: Dict[str, Any]):
    """
    Create a track object from configuration dictionary.
    
    Args:
        track_config: Dictionary with track parameters
        
    Returns:
        Track object
    """
    track_type = track_config.get('type')
    
    if not track_type:
        raise ValueError("Track configuration must specify 'type'")
    
    if track_type == 'hic_triangle':
        return _create_hic_triangle_track(track_config)
    elif track_type == 'bigwig':
        return _create_bigwig_track(track_config)
    elif track_type == 'bed':
        return _create_bed_track(track_config)
    elif track_type == 'bedpe':
        return _create_bedpe_track(track_config)
    elif track_type == 'gene':
        return _create_gene_track(track_config)
    else:
        raise ValueError(f"Unknown track type: {track_type}")


def _create_hic_triangle_track(config: Dict[str, Any]) -> HiCTriangleTrack:
    """Create HiCTriangleTrack from config."""
    filepath = config.get('file')
    if not filepath:
        raise ValueError("Hi-C track requires 'file' parameter")
    
    resolution = config.get('resolution')
    if not resolution:
        raise ValueError("Hi-C track requires 'resolution' parameter")
    
    # Determine file type and create provider
    filepath = Path(filepath)
    if str(filepath).endswith('.hic'):
        provider = HicMatrixProvider(str(filepath))
    elif str(filepath).endswith(('.mcool', '.cool')):
        provider = CoolerMatrixProvider(str(filepath), resolution=resolution)
    else:
        raise ValueError(f"Unknown Hi-C file format: {filepath}")
    
    return HiCTriangleTrack(
        matrix_provider=provider,
        resolution=resolution,
        norm=config.get('norm', 'KR'),
        cmap=config.get('cmap', 'OrRd'),
        vmin=config.get('vmin'),
        vmax=config.get('vmax'),
        name=config.get('name', 'Hi-C'),
        height=config.get('height', 2.0)
    )


def _create_bigwig_track(config: Dict[str, Any]) -> BigWigTrack:
    """Create BigWigTrack from config."""
    filepath = config.get('file')
    if not filepath:
        raise ValueError("BigWig track requires 'file' parameter")
    
    return BigWigTrack(
        filepath=filepath,
        name=config.get('name'),
        color=config.get('color', '#1a5276'),
        alpha=config.get('alpha', 0.8),
        style=config.get('style', 'fill'),
        height=config.get('height', 1.0),
        ylim=config.get('ylim')
    )


def _create_bed_track(config: Dict[str, Any]) -> BedTrack:
    """Create BedTrack from config."""
    filepath = config.get('file')
    if not filepath:
        raise ValueError("BED track requires 'file' parameter")
    
    return BedTrack(
        filepath=filepath,
        name=config.get('name'),
        color=config.get('color', '#8B1538'),
        alpha=config.get('alpha', 0.85),
        height=config.get('height', 0.5)
    )


def _create_bedpe_track(config: Dict[str, Any]) -> BedPETrack:
    """Create BedPETrack from config."""
    filepath = config.get('file')
    if not filepath:
        raise ValueError("BEDPE track requires 'file' parameter")
    
    return BedPETrack(
        filepath=filepath,
        name=config.get('name'),
        color=config.get('color', '#0d1b2a'),
        alpha=config.get('alpha', 0.75),
        style=config.get('style', 'arc'),
        height=config.get('height', 1.0)
    )


def _create_gene_track(config: Dict[str, Any]) -> GeneTrack:
    """Create GeneTrack from config."""
    filepath = config.get('file')
    if not filepath:
        raise ValueError("Gene track requires 'file' parameter")
    
    return GeneTrack(
        filepath=filepath,
        name=config.get('name', 'Genes'),
        gene_color=config.get('gene_color', 'midnightblue'),
        exon_color=config.get('exon_color', 'darkblue'),
        height=config.get('height', 1.5),
        show_gene_names=config.get('show_gene_names', True),
        max_rows=config.get('max_rows', 5),
        max_genes=config.get('max_genes', 10),
        query_gene=config.get('query_gene')
    )

