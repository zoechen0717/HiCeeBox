"""Abstract base class for Hi-C matrix data providers."""

from abc import ABC, abstractmethod
import numpy as np
from typing import Tuple


class MatrixProvider(ABC):
    """
    Abstract base class for accessing Hi-C contact matrices.
    
    This interface abstracts away differences between .hic and .mcool file formats,
    providing a unified API for fetching contact matrices.
    """
    
    @abstractmethod
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
            chrom: Chromosome name (e.g., 'chr1')
            start: Start position in base pairs
            end: End position in base pairs
            resolution: Bin size in base pairs
            norm: Normalization method (e.g., 'KR', 'VC', 'NONE')
            
        Returns:
            tuple: (matrix, bins)
                - matrix: Square contact matrix as np.ndarray
                - bins: Array of bin start positions
        """
        pass
    
    @abstractmethod
    def get_resolutions(self) -> list[int]:
        """
        Get available resolutions in the file.
        
        Returns:
            List of available resolutions in base pairs
        """
        pass
    
    @abstractmethod
    def get_chromosomes(self) -> list[str]:
        """
        Get list of chromosome names in the file.
        
        Returns:
            List of chromosome names
        """
        pass

