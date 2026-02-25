"""Genomic utilities for coordinate handling and formatting."""

import re
from pathlib import Path
from typing import Tuple, Optional, List


def parse_region(region_str: str) -> Tuple[str, int, int]:
    """
    Parse genomic region string into components.
    
    Args:
        region_str: Region string in format 'chr:start-end' or 'chr:start,start-end,end'
                   (commas are stripped)
        
    Returns:
        tuple: (chrom, start, end)
        
    Examples:
        >>> parse_region('chr6:30000000-32000000')
        ('chr6', 30000000, 32000000)
        >>> parse_region('chr6:30,000,000-32,000,000')
        ('chr6', 30000000, 32000000)
    """
    # Remove commas
    region_str = region_str.replace(',', '')
    
    # Try standard format: chr:start-end
    match = re.match(r'^(\w+):(\d+)-(\d+)$', region_str)
    
    if not match:
        raise ValueError(
            f"Invalid region format: {region_str}. "
            "Expected format: 'chr:start-end' (e.g., 'chr6:30000000-32000000')"
        )
    
    chrom = match.group(1)
    start = int(match.group(2))
    end = int(match.group(3))
    
    if start >= end:
        raise ValueError(f"Start position must be less than end position: {start} >= {end}")
    
    return chrom, start, end


def format_position(position: int, separator: str = ',') -> str:
    """
    Format genomic position with thousand separators.
    
    Args:
        position: Position in base pairs
        separator: Separator character (default: comma)
        
    Returns:
        Formatted position string
        
    Example:
        >>> format_position(30000000)
        '30,000,000'
    """
    return f"{position:,}".replace(',', separator)


def format_region(chrom: str, start: int, end: int, separator: str = ',') -> str:
    """
    Format genomic region as string.
    
    Args:
        chrom: Chromosome name
        start: Start position
        end: End position
        separator: Thousand separator (default: comma)
        
    Returns:
        Formatted region string
        
    Example:
        >>> format_region('chr6', 30000000, 32000000)
        'chr6:30,000,000-32,000,000'
    """
    start_str = format_position(start, separator)
    end_str = format_position(end, separator)
    return f"{chrom}:{start_str}-{end_str}"


def get_region_size(start: int, end: int) -> int:
    """
    Calculate region size.
    
    Args:
        start: Start position
        end: End position
        
    Returns:
        Region size in base pairs
    """
    return end - start


def overlap(
    start1: int, end1: int, 
    start2: int, end2: int
) -> Optional[Tuple[int, int]]:
    """
    Calculate overlap between two intervals.
    
    Args:
        start1: Start of first interval
        end1: End of first interval
        start2: Start of second interval
        end2: End of second interval
        
    Returns:
        Overlap interval (start, end) or None if no overlap
    """
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    
    if overlap_start < overlap_end:
        return (overlap_start, overlap_end)
    else:
        return None


def contains(
    outer_start: int, outer_end: int,
    inner_start: int, inner_end: int
) -> bool:
    """
    Check if one interval contains another.
    
    Args:
        outer_start: Start of outer interval
        outer_end: End of outer interval
        inner_start: Start of inner interval
        inner_end: End of inner interval
        
    Returns:
        True if outer interval contains inner interval
    """
    return outer_start <= inner_start and inner_end <= outer_end


def clamp(value: int, min_val: int, max_val: int) -> int:
    """
    Clamp value to range.
    
    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value
        
    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


def region_from_gene_promoter(
    gene_name: str,
    promoter_bed_path: str,
    upstream: int = 25000,
    downstream: int = 25000,
    name_column: int = 4,
) -> Tuple[str, int, int]:
    """
    Get genomic region (chrom, start, end) for a gene from a promoter BED file,
    extended by upstream/downstream. Use this to set GenomeView region by gene.
    
    BED must have at least 4 columns: chrom, start, end, name (name in column 4).
    Gene name is matched against the name column (exact or strip); first match is used.
    
    Args:
        gene_name: Gene symbol or identifier (e.g. 'MYC', 'BRCA1')
        promoter_bed_path: Path to BED with promoter intervals (chrom, start, end, name)
        upstream: Base pairs to extend upstream of promoter start (default 25000)
        downstream: Base pairs to extend downstream of promoter end (default 25000)
        name_column: 1-based column index for gene name (default 4 = 4th column)
        
    Returns:
        (chrom, start, end) for the region [promoter_start - upstream, promoter_end + downstream],
        with start clamped to 0.
        
    Raises:
        FileNotFoundError: If promoter BED does not exist
        ValueError: If gene_name not found in BED
        
    Example:
        >>> chrom, start, end = region_from_gene_promoter('MYC', 'promoters.bed', 25000, 25000)
        >>> view = GenomeView(chrom=chrom, start=start, end=end)
    """
    path = Path(promoter_bed_path)
    if not path.exists():
        raise FileNotFoundError(f"Promoter BED not found: {path}")
    idx = name_column - 1  # 0-based
    if idx < 0:
        raise ValueError("name_column must be >= 1")
    chrom, start, end = None, None, None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("track"):
                continue
            fields = line.split("\t")
            if len(fields) <= idx:
                continue
            name = fields[idx].strip()
            if name != gene_name:
                continue
            try:
                chrom = fields[0]
                start = int(fields[1])
                end = int(fields[2])
            except (ValueError, IndexError):
                continue
            break
    if chrom is None or start is None or end is None:
        raise ValueError(f"Gene '{gene_name}' not found in {promoter_bed_path}")
    region_start = max(0, start - upstream)
    region_end = end + downstream
    return chrom, region_start, region_end


def list_genes_in_promoter_bed(promoter_bed_path: str, name_column: int = 4) -> List[str]:
    """
    List all gene names in a promoter BED (useful to see valid names for region_from_gene_promoter).
    
    Args:
        promoter_bed_path: Path to BED file
        name_column: 1-based column index for gene name (default 4)
        
    Returns:
        List of unique gene names in order of first appearance
    """
    path = Path(promoter_bed_path)
    if not path.exists():
        raise FileNotFoundError(f"Promoter BED not found: {path}")
    idx = name_column - 1
    seen = set()
    names = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("track"):
                continue
            fields = line.split("\t")
            if len(fields) <= idx:
                continue
            name = fields[idx].strip()
            if name and name not in seen:
                seen.add(name)
                names.append(name)
    return names

