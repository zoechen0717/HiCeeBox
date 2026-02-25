"""HiC (.hic) matrix provider implementation."""

import numpy as np
from typing import Tuple
from pathlib import Path

from hiceebox.matrix.base import MatrixProvider


class HicMatrixProvider(MatrixProvider):
    """
    Matrix provider for .hic files using hicstraw.
    
    Supports Juicer .hic format files.
    """
    
    def __init__(self, filepath: str):
        """
        Initialize .hic matrix provider.
        
        Args:
            filepath: Path to .hic file
        """
        self.filepath = Path(filepath)
        self._hic = None
        self._validate_file()
    
    def _validate_file(self) -> None:
        """Validate that the file exists."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"HiC file not found: {self.filepath}")
    
    def _get_hic(self):
        """
        Lazy-load hicstraw HiCFile object.
        
        Returns:
            HiCFile object
        """
        if self._hic is None:
            try:
                import hicstraw
            except ImportError:
                raise ImportError(
                    "hicstraw library is required for .hic files. "
                    "Install with: pip install hicstraw"
                )
            
            self._hic = hicstraw.HiCFile(str(self.filepath))
        
        return self._hic
    
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
            resolution: Bin size
            norm: Normalization method
            
        Returns:
            tuple: (matrix, bins)
        """
        hic = self._get_hic()
        
        try:
            import hicstraw
        except ImportError:
            raise ImportError("hicstraw library is required")
        
        # Fetch matrix data
        try:
            # Normalize chromosome name - try both with and without "chr" prefix
            chrom_variants = [chrom]
            if chrom.startswith("chr"):
                chrom_variants.append(chrom[3:])  # Remove "chr" prefix
            else:
                chrom_variants.append(f"chr{chrom}")  # Add "chr" prefix
            
            # Try different normalization methods if KR fails
            norm_variants = [norm] if norm.upper() != "NONE" else ["NONE"]
            if norm.upper() != "VC":
                norm_variants.append("VC")
            if norm.upper() != "NONE":
                norm_variants.append("NONE")
            
            mzd = None
            last_error = None
            
            # Try different combinations of chromosome name and normalization
            for chrom_var in chrom_variants:
                for norm_var in norm_variants:
                    try:
                        mzd = hic.getMatrixZoomData(
                            chrom_var, chrom_var, "observed", norm_var, "BP", resolution
                        )
                        # If successful, break out of loops
                        norm = norm_var
                        chrom = chrom_var
                        break
                    except Exception as e:
                        last_error = e
                        continue
                if mzd is not None:
                    break
            
            if mzd is None:
                # If all combinations failed, try with original parameters to get better error
                try:
                    mzd = hic.getMatrixZoomData(
                        chrom, chrom, "observed", norm, "BP", resolution
                    )
                except Exception as e:
                    # Provide more helpful error message
                    available_chroms = [c.name for c in hic.getChromosomes()]
                    available_resolutions = hic.getResolutions()
                    raise RuntimeError(
                        f"Error fetching data from .hic file: {e}\n"
                        f"  Chromosome: {chrom} (available: {available_chroms[:5]}...)\n"
                        f"  Resolution: {resolution} (available: {available_resolutions[:5]}...)\n"
                        f"  Normalization: {norm}\n"
                        f"  Region: {start}-{end}"
                    ) from e
            
            # Get records in the region
            records = mzd.getRecords(start, end, start, end)
            
            # Build dense matrix
            # Calculate number of bins
            nbins = (end - start) // resolution
            if nbins <= 0:
                raise ValueError(f"Invalid region size: {end - start} bp at resolution {resolution}")
            
            # Generate bins aligned to resolution
            # Ensure bins and matrix have matching dimensions
            bins = np.arange(start, start + nbins * resolution, resolution)
            
            # Ensure bins array matches matrix dimensions
            if len(bins) > nbins:
                bins = bins[:nbins]  # Trim if too many
            elif len(bins) < nbins:
                # Add missing bins if needed
                last_bin = bins[-1] if len(bins) > 0 else start
                additional_bins = np.arange(last_bin + resolution, start + nbins * resolution, resolution)
                bins = np.concatenate([bins, additional_bins])
            
            # Ensure exactly nbins bins
            bins = bins[:nbins]
            
            matrix = np.zeros((nbins, nbins), dtype=np.float64)
            
            for record in records:
                i = (record.binX - start) // resolution
                j = (record.binY - start) // resolution
                # Ensure indices are within bounds
                if 0 <= i < nbins and 0 <= j < nbins:
                    matrix[i, j] = record.counts
                    if i != j:
                        matrix[j, i] = record.counts
            
            return matrix, bins
            
        except RuntimeError:
            # Re-raise RuntimeError with enhanced message
            raise
        except Exception as e:
            # Provide more context for other errors
            error_msg = str(e)
            try:
                available_chroms = [c.name for c in hic.getChromosomes()]
                available_resolutions = hic.getResolutions()
                raise RuntimeError(
                    f"Error fetching data from .hic file: {error_msg}\n"
                    f"  Chromosome: {chrom} (available: {available_chroms[:5]}...)\n"
                    f"  Resolution: {resolution} (available: {available_resolutions[:5]}...)\n"
                    f"  Normalization: {norm}\n"
                    f"  Region: {start}-{end}"
                ) from e
            except:
                # If we can't get metadata, just re-raise original error
                raise RuntimeError(f"Error fetching data from .hic file: {error_msg}") from e
    
    def get_resolutions(self) -> list[int]:
        """
        Get available resolutions.
        
        Returns:
            List of available resolutions
        """
        hic = self._get_hic()
        return hic.getResolutions()
    
    def get_chromosomes(self) -> list[str]:
        """
        Get list of chromosomes.
        
        Returns:
            List of chromosome names
        """
        hic = self._get_hic()
        return [chrom.name for chrom in hic.getChromosomes()]
    
    def get_chromosome_info(self, chrom: str) -> dict:
        """
        Get chromosome information (name and length).
        
        Args:
            chrom: Chromosome name
            
        Returns:
            Dictionary with 'name' and 'length' keys
        """
        hic = self._get_hic()
        for chrom_obj in hic.getChromosomes():
            if chrom_obj.name == chrom:
                return {
                    'name': chrom_obj.name,
                    'length': chrom_obj.length
                }
        raise ValueError(f"Chromosome {chrom} not found in file")
    
    def get_all_chromosomes_info(self) -> list[dict]:
        """
        Get information for all chromosomes.
        
        Returns:
            List of dictionaries with 'name' and 'length' keys
        """
        hic = self._get_hic()
        return [
            {'name': chrom.name, 'length': chrom.length}
            for chrom in hic.getChromosomes()
        ]
    
    def get_available_normalizations(self, chrom: str = None, resolution: int = None) -> list[str]:
        """
        Get available normalization methods for the HIC file.
        
        Args:
            chrom: Optional chromosome name to test (if None, uses first chromosome)
            resolution: Optional resolution to test (if None, uses first available resolution)
            
        Returns:
            List of available normalization method names (e.g., ['KR', 'VC', 'VC_SQRT', 'SCALE'])
        """
        hic = self._get_hic()
        
        # Use first chromosome and resolution if not specified
        if chrom is None:
            chromosomes = hic.getChromosomes()
            if not chromosomes:
                return []
            chrom = chromosomes[0].name
        
        if resolution is None:
            resolutions = hic.getResolutions()
            if not resolutions:
                return []
            resolution = resolutions[0]
        
        # Common normalization methods to test
        norm_candidates = ['KR', 'VC', 'VC_SQRT', 'SCALE', 'NONE', 'GW_KR', 'GW_VC', 'INTER_KR', 'INTER_VC']
        available_norms = []
        
        # Test each normalization method
        for norm in norm_candidates:
            try:
                mzd = hic.getMatrixZoomData(chrom, chrom, "observed", norm, "BP", resolution)
                # If successful, this normalization is available
                available_norms.append(norm)
            except:
                # This normalization is not available, skip it
                continue
        
        return available_norms

