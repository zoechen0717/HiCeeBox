"""Hi-C whole genome view track (chromosome vs chromosome matrix)."""

from typing import Tuple, Optional, List, Dict
import matplotlib.pyplot as plt
import numpy as np

from hiceebox.tracks.base import Track
from hiceebox.matrix.base import MatrixProvider


class HiCGenomeViewTrack(Track):
    """
    Track for displaying whole-genome Hi-C view (all chromosomes).
    
    Displays a chromosome vs chromosome matrix where:
    - Diagonal blocks show intra-chromosomal contacts
    - Off-diagonal blocks show inter-chromosomal contacts
    """
    
    def __init__(
        self,
        matrix_provider: MatrixProvider,
        resolution: int,
        norm: str = "KR",
        cmap: str = "OrRd",
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        name: Optional[str] = "Whole Genome Hi-C",
        height: float = 3.0,
        pad_top: float = 0.1,
        pad_bottom: float = 0.05,
        max_chromosomes: int = 25  # Limit number of chromosomes for performance
    ):
        """
        Initialize whole-genome Hi-C view track.
        
        Args:
            matrix_provider: MatrixProvider instance for fetching Hi-C data
            resolution: Bin size in base pairs (should be coarse, e.g., 1Mb)
            norm: Normalization method (e.g., 'KR', 'VC', 'NONE')
            cmap: Matplotlib colormap name
            vmin: Minimum value for color scale
            vmax: Maximum value for color scale
            name: Track name
            height: Relative height weight
            pad_top: Top padding fraction (for chromosome labels)
            pad_bottom: Bottom padding fraction
            max_chromosomes: Maximum number of chromosomes to display
        """
        super().__init__(name=name, height=height, pad_top=pad_top, pad_bottom=pad_bottom)
        self.matrix_provider = matrix_provider
        self.resolution = resolution
        self.norm = norm
        self.cmap = cmap
        self.vmin = vmin
        self.vmax = vmax
        self.max_chromosomes = max_chromosomes
        # Store actual vmin/vmax used in rendering
        self.actual_vmin: Optional[float] = None
        self.actual_vmax: Optional[float] = None
        
        # Get chromosome information
        self.chromosomes = matrix_provider.get_chromosomes()
        if hasattr(matrix_provider, 'get_all_chromosomes_info'):
            self.chrom_info = matrix_provider.get_all_chromosomes_info()
        else:
            # Fallback: create basic chromosome info
            self.chrom_info = []
            for chrom in self.chromosomes:
                try:
                    info = matrix_provider.get_chromosome_info(chrom)
                    self.chrom_info.append(info)
                except:
                    pass
        
        # Limit chromosomes if too many
        if len(self.chromosomes) > self.max_chromosomes:
            self.chromosomes = self.chromosomes[:self.max_chromosomes]
            self.chrom_info = self.chrom_info[:self.max_chromosomes]
    
    def draw(self, ax: plt.Axes, region: Tuple[str, int, int]) -> None:
        """
        Draw whole-genome Hi-C view (chromosome vs chromosome matrix).
        
        Args:
            ax: Matplotlib Axes to draw on
            region: Genomic region (ignored for whole genome view)
        """
        if not self.chrom_info or len(self.chromosomes) == 0:
            ax.text(
                0.5, 0.5,
                "No chromosome information available for whole genome view.",
                transform=ax.transAxes,
                ha='center', va='center',
                fontsize=9, color='gray'
            )
            self.format_axis(ax, show_xlabel=False)
            return
        
        # Calculate cumulative chromosome positions for positioning blocks
        cum_lengths = [0]
        chrom_lengths = []
        for chrom_obj in self.chrom_info:
            length = chrom_obj['length']
            chrom_lengths.append(length)
            cum_lengths.append(cum_lengths[-1] + length)
        
        total_length = cum_lengths[-1]
        num_chroms = len(self.chromosomes)
        
        # Build the genome-wide matrix
        # Each cell (i, j) represents contacts between chromosome i and chromosome j
        genome_matrix = np.zeros((num_chroms, num_chroms))
        
        # Sample data for each chromosome pair
        # For intra-chromosomal (diagonal), sample a central region
        # For inter-chromosomal (off-diagonal), sample contacts between chromosomes
        all_values = []
        
        # Print debug info
        print(f"Drawing whole genome view: {num_chroms} chromosomes, resolution={self.resolution}, norm={self.norm}")
        
        try:
            for i in range(num_chroms):
                chrom_i = self.chromosomes[i]
                
                for j in range(num_chroms):
                    chrom_j = self.chromosomes[j]
                    
                    try:
                        # Sample a representative region from each chromosome
                        # For intra-chromosomal: use central region
                        # For inter-chromosomal: use central regions of both chromosomes
                        
                        if i == j:
                            # Intra-chromosomal: sample central region
                            length_i = chrom_lengths[i]
                            sample_start = max(0, length_i // 4)
                            sample_end = min(length_i, length_i * 3 // 4)
                            
                            if sample_end - sample_start > self.resolution:
                                # Try different normalization methods if the selected one fails
                                # For whole genome view at low resolution, NONE is often the only available
                                norm_to_try = ["NONE", self.norm, "VC"]
                                matrix = None
                                
                                for norm_attempt in norm_to_try:
                                    try:
                                        matrix, bins = self.matrix_provider.fetch(
                                            chrom_i, sample_start, sample_end, 
                                            self.resolution, norm_attempt
                                        )
                                        if matrix.size > 0:
                                            break
                                    except Exception as e:
                                        # Try next normalization - suppress error messages for whole genome view
                                        continue
                                
                                if matrix is not None and matrix.size > 0:
                                    # Use average contact density from diagonal
                                    n = min(matrix.shape[0], matrix.shape[1])
                                    if n > 0:
                                        # Sample diagonal elements (close contacts)
                                        diag_values = [matrix[k, k] for k in range(min(10, n)) if not np.isnan(matrix[k, k])]
                                        if diag_values:
                                            avg_value = np.mean(diag_values)
                                            genome_matrix[i, j] = avg_value
                                            all_values.append(avg_value)
                        
                        else:
                            # Inter-chromosomal: fetch contacts between two different chromosomes
                            # Need to use hicstraw directly for inter-chromosomal contacts
                            length_i = chrom_lengths[i]
                            length_j = chrom_lengths[j]
                            
                            # Sample central regions of both chromosomes
                            sample_start_i = max(0, length_i // 4)
                            sample_end_i = min(length_i, length_i * 3 // 4)
                            sample_start_j = max(0, length_j // 4)
                            sample_end_j = min(length_j, length_j * 3 // 4)
                            
                            try:
                                # Directly use hicstraw for inter-chromosomal contacts
                                # The provider's fetch method only supports same chromosome
                                if hasattr(self.matrix_provider, '_get_hic'):
                                    hic = self.matrix_provider._get_hic()
                                    import hicstraw
                                    
                                    # Try different chromosome name variants
                                    chrom_i_variants = [chrom_i]
                                    if chrom_i.startswith("chr"):
                                        chrom_i_variants.append(chrom_i[3:])
                                    else:
                                        chrom_i_variants.append(f"chr{chrom_i}")
                                    
                                    chrom_j_variants = [chrom_j]
                                    if chrom_j.startswith("chr"):
                                        chrom_j_variants.append(chrom_j[3:])
                                    else:
                                        chrom_j_variants.append(f"chr{chrom_j}")
                                    
                                    # Try different combinations of chromosome names and normalizations
                                    # For inter-chromosomal at low resolution, NONE is often the only available
                                    mzd = None
                                    norms_to_try = ["NONE", self.norm, "VC"]
                                    
                                    for norm_attempt in norms_to_try:
                                        for ci in chrom_i_variants:
                                            for cj in chrom_j_variants:
                                                try:
                                                    mzd = hic.getMatrixZoomData(
                                                        ci, cj, "observed", norm_attempt, "BP", self.resolution
                                                    )
                                                    break
                                                except:
                                                    continue
                                            if mzd is not None:
                                                break
                                        if mzd is not None:
                                            break
                                    
                                    if mzd is not None:
                                        # Get records for the inter-chromosomal region
                                        records = mzd.getRecords(sample_start_i, sample_end_i, 
                                                                 sample_start_j, sample_end_j)
                                        
                                        if records and len(records) > 0:
                                            # Calculate average contact value
                                            values = [r.counts for r in records if r.counts > 0]
                                            if values:
                                                avg_value = np.mean(values)
                                                genome_matrix[i, j] = avg_value
                                                all_values.append(avg_value)
                            except Exception as e:
                                # Inter-chromosomal contacts might not be available
                                # This is normal - many HIC files only contain intra-chromosomal data
                                # Suppress common error messages (they're printed by hicstraw library)
                                pass
                    
                    except Exception as e:
                        # Skip if data not available for this chromosome pair
                        # Don't print warnings for every failed chromosome pair to avoid spam
                        # Only print if it's a significant issue
                        if "Error finding block data" not in str(e) and "normalization vectors" not in str(e):
                            print(f"Warning: Could not fetch data for {chrom_i} vs {chrom_j}: {e}")
                        continue
            
            if len(all_values) == 0:
                print(f"Warning: No Hi-C data collected for whole genome view. Tried {num_chroms}x{num_chroms} chromosome pairs.")
                ax.text(
                    0.5, 0.5,
                    f"No Hi-C data available for whole genome view.\nTried {num_chroms} chromosomes at {self.resolution:,} bp resolution.\nTry a different resolution or normalization.",
                    transform=ax.transAxes,
                    ha='center', va='center',
                    fontsize=9, color='gray'
                )
                self.format_axis(ax, show_xlabel=False)
                return
            
            print(f"Collected {len(all_values)} data points for whole genome view")
            
            # Determine color scale
            all_values_array = np.array(all_values)
            valid_values = all_values_array[~np.isnan(all_values_array)]
            
            if len(valid_values) == 0:
                ax.text(
                    0.5, 0.5,
                    "No valid Hi-C data for whole genome view.",
                    transform=ax.transAxes,
                    ha='center', va='center',
                    fontsize=9, color='gray'
                )
                self.format_axis(ax, show_xlabel=False)
                return
            
            # Log transform for better visualization
            log_matrix = np.log10(genome_matrix + 1)
            
            # Determine vmin/vmax
            log_values = np.log10(valid_values + 1)
            if self.vmin is not None:
                vmin = self.vmin
            else:
                vmin = np.nanpercentile(log_values, 5)
            
            if self.vmax is not None:
                vmax = self.vmax
            else:
                vmax = np.nanpercentile(log_values, 95)
            
            self.actual_vmin = vmin
            self.actual_vmax = vmax
            
            # Create position arrays for pcolormesh
            x_edges = cum_lengths
            y_edges = cum_lengths
            
            # Expand log_matrix to match edges
            # For each chromosome pair (i, j), we need to fill the corresponding block
            expanded_matrix = np.zeros((len(y_edges) - 1, len(x_edges) - 1))
            
            for i in range(num_chroms):
                for j in range(num_chroms):
                    # Fill the block corresponding to chromosome i (y) vs chromosome j (x)
                    expanded_matrix[i:(i+1), j:(j+1)] = log_matrix[i, j]
            
            # Create meshgrid
            X, Y = np.meshgrid(x_edges, y_edges)
            
            # Draw the heatmap
            im = ax.pcolormesh(
                X, Y, expanded_matrix,
                cmap=self.cmap,
                vmin=vmin,
                vmax=vmax,
                rasterized=True
            )
            
            # Add chromosome boundaries and labels
            for i, chrom_obj in enumerate(self.chrom_info):
                # Vertical boundaries
                ax.axvline(cum_lengths[i], color='black', linewidth=0.5, alpha=0.3)
                # Horizontal boundaries
                ax.axhline(cum_lengths[i], color='black', linewidth=0.5, alpha=0.3)
                
                # Add chromosome labels on x-axis (top)
                mid_pos = cum_lengths[i] + chrom_lengths[i] / 2
                chrom_name = chrom_obj['name'].replace('chr', '')
                ax.text(
                    mid_pos, total_length * 1.01,
                    chrom_name,
                    ha='center', va='bottom',
                    fontsize=7,
                    transform=ax.get_xaxis_transform()
                )
                
                # Add chromosome labels on y-axis (left)
                ax.text(
                    total_length * -0.01, mid_pos,
                    chrom_name,
                    ha='right', va='center',
                    fontsize=7,
                    transform=ax.get_yaxis_transform()
                )
            
            # Set limits
            ax.set_xlim(0, total_length)
            ax.set_ylim(0, total_length)
            ax.set_aspect('equal', adjustable='box')
            
            # Add colorbar
            import matplotlib.cm as cm
            from matplotlib.colors import Normalize
            norm = Normalize(vmin=vmin, vmax=vmax)
            sm = plt.cm.ScalarMappable(cmap=self.cmap, norm=norm)
            sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax, label='Log10(Contact + 1)', fraction=0.05)
            cbar.ax.tick_params(labelsize=8)
            
            self.format_axis(ax, show_xlabel=False)
            ax.set_title(self.name, fontsize=10)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            ax.text(
                0.5, 0.5,
                f"Error rendering whole genome view: {e}",
                transform=ax.transAxes,
                ha='center', va='center',
                fontsize=9, color='red'
            )
            self.format_axis(ax, show_xlabel=False)
