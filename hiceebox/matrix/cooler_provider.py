"""Cooler (.mcool) matrix provider implementation."""

import numpy as np
from typing import Tuple, Optional
from pathlib import Path

from hiceebox.matrix.base import MatrixProvider


class CoolerMatrixProvider(MatrixProvider):
    """
    Matrix provider for .mcool files using the cooler library.
    
    Supports multi-resolution cooler files (.mcool) and single-resolution
    cooler files (.cool).
    """
    
    def __init__(self, filepath: str, resolution: Optional[int] = None):
        """
        Initialize cooler matrix provider.
        
        Args:
            filepath: Path to .mcool or .cool file
            resolution: Resolution in base pairs (required for .mcool files)
        """
        self.filepath = Path(filepath)
        self.resolution = resolution
        self._cooler = None
        self._validate_file()
    
    def _validate_file(self) -> None:
        """Validate that the file exists and is accessible."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"Cooler file not found: {self.filepath}")
    
    def _get_cooler(self):
        """
        Lazy-load cooler object.
        
        Returns:
            Cooler object for the specified resolution
        """
        if self._cooler is None:
            try:
                import cooler
            except ImportError:
                raise ImportError(
                    "cooler library is required for .mcool files. "
                    "Install with: pip install cooler"
                )
            
            # Handle multi-resolution .mcool files
            if str(self.filepath).endswith('.mcool'):
                if self.resolution is None:
                    raise ValueError(
                        "resolution must be specified for .mcool files"
                    )
                uri = f"{self.filepath}::/resolutions/{self.resolution}"
                self._cooler = cooler.Cooler(uri)
            else:
                self._cooler = cooler.Cooler(str(self.filepath))
        
        return self._cooler
    
    def fetch(
        self, 
        chrom: str, 
        start: int, 
        end: int, 
        resolution: int, 
        norm: str = "KR"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fetch contact matrix for a genomic region.
        
        Args:
            chrom: Chromosome name
            start: Start position
            end: End position
            resolution: Bin size (must match cooler resolution)
            norm: Normalization method
            
        Returns:
            tuple: (matrix, bins)
        """
        clr = self._get_cooler()
        
        # Fetch matrix
        region = f"{chrom}:{start}-{end}"
        
        try:
            matrix = clr.matrix(balance=(norm.lower() if norm != "NONE" else False)).fetch(region)
            bins = clr.bins().fetch(region)['start'].values
        except Exception as e:
            raise RuntimeError(f"Error fetching data from cooler: {e}")
        
        return matrix, bins
    
    def get_resolutions(self) -> list[int]:
        """
        Get available resolutions.
        
        Returns:
            List of available resolutions
        """
        try:
            import cooler
        except ImportError:
            raise ImportError("cooler library is required")
        
        if str(self.filepath).endswith('.mcool'):
            try:
                resolutions = cooler.fileops.list_coolers(str(self.filepath))
                # Extract resolution values from URIs
                return sorted([
                    int(uri.split('/')[-1]) 
                    for uri in resolutions
                ])
            except Exception:
                return []
        else:
            clr = self._get_cooler()
            return [clr.binsize]
    
    def get_chromosomes(self) -> list[str]:
        """
        Get list of chromosomes.
        
        Returns:
            List of chromosome names
        """
        clr = self._get_cooler()
        return clr.chromnames
    
    def get_chromosome_info(self, chrom: str) -> dict:
        """
        Get chromosome information (name and length).
        
        Args:
            chrom: Chromosome name
            
        Returns:
            Dictionary with 'name' and 'length' keys
        """
        clr = self._get_cooler()
        chromsizes = clr.chromsizes
        if chrom not in chromsizes:
            raise ValueError(f"Chromosome {chrom} not found in file")
        return {
            'name': chrom,
            'length': int(chromsizes[chrom])
        }
    
    def get_all_chromosomes_info(self) -> list[dict]:
        """
        Get information for all chromosomes.
        
        Returns:
            List of dictionaries with 'name' and 'length' keys
        """
        clr = self._get_cooler()
        chromsizes = clr.chromsizes
        return [
            {'name': chrom, 'length': int(length)}
            for chrom, length in chromsizes.items()
        ]

