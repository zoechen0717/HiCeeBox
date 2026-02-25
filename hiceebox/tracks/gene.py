"""Gene annotation track for GTF/BED12 files."""

from typing import Tuple, Optional, List, Dict
from pathlib import Path
import random
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
import gzip

from hiceebox.tracks.base import Track

# Window-size thresholds (bp) for BED12 draw strategy
WINDOW_LARGE = 2_000_000   # > 2 Mb: names only
WINDOW_MEDIUM = 50_000     # 50 kb < window <= 2 Mb: line + strand
# window <= 50 kb: full BED12 exons

# Bin sizes (bp) for cache tiers, used as bin_size in cache key
BIN_SIZE_LARGE = 1_000_000   # 1 Mb
BIN_SIZE_MEDIUM = 50_000     # 50 kb
BIN_SIZE_SMALL = 10_000      # 10 kb


class GeneTrack(Track):
    """
    Track for displaying gene annotations from GTF or BED12 files.
    
    Displays genes with exons, introns, and gene names.
    """
    
    def __init__(
        self,
        filepath: str,
        name: Optional[str] = "Genes",
        gene_color: str = "midnightblue",
        exon_color: str = "darkblue",
        height: float = 1.5,
        scale: float = 1.0,
        pad_top: float = 0.05,
        pad_bottom: float = 0.05,
        show_gene_names: bool = True,
        max_rows: int = 5,
        max_genes: int = 10,
        query_gene: Optional[str] = None,
        intron_height: float = 0.15,
        exon_height: float = 0.4,
        layout_mode: str = "expanded",
        gene_fontsize: float = 7.0
    ):
        """
        Initialize gene track.
        
        Args:
            filepath: Path to GTF or BED12 file
            name: Track name
            gene_color: Color for gene body/introns
            exon_color: Color for exons
            height: Relative height weight
            scale: Height multiplier (effective height = height * scale)
            pad_top: Top padding fraction
            pad_bottom: Bottom padding fraction
            show_gene_names: Whether to display gene names
            max_rows: Maximum number of gene rows to display (expanded mode)
            max_genes: Maximum number of genes to display (default 10). When
                       query_gene is set, that gene is always included.
            query_gene: If set (e.g. when region was chosen by gene name),
                        this gene is always shown and counts toward max_genes.
            intron_height: Height of intron line (0-1 scale per row)
            exon_height: Height of exon boxes (0-1 scale per row)
            layout_mode: 'expanded' = multiple rows to avoid overlap;
                         'condensed' = single row, genes may overlap (compact)
            gene_fontsize: Font size for gene name labels (default 7)
        """
        super().__init__(name=name, height=height, scale=scale, pad_top=pad_top, pad_bottom=pad_bottom)
        
        self.filepath = Path(filepath)
        self.gene_color = gene_color
        self.exon_color = exon_color
        self.show_gene_names = show_gene_names
        self.max_rows = max_rows
        self.max_genes = max(1, max_genes)
        self.query_gene = query_gene.strip() if query_gene else None
        self.intron_height = intron_height
        self.exon_height = exon_height
        self.layout_mode = layout_mode if layout_mode in ("expanded", "condensed") else "expanded"
        self.gene_fontsize = max(4.0, min(20.0, float(gene_fontsize)))
        
        self._genes = None  # Cached gene structures (GTF path)
        # BED12 path: index by chrom (sorted by start), cache by (chrom, bin_id, bin_size)
        self._bed12_index: Optional[Dict[str, List[Dict]]] = None
        # key = (track_id, chrom, bin_id, bin_size), value = list of transcript dicts
        self._bed12_cache: Dict[Tuple[Tuple[str, str], str, int, int], List[Dict]] = {}
        
        self._validate_file()
    
    def _validate_file(self) -> None:
        """Validate that the file exists."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"Gene file not found: {self.filepath}")
    
    def _open_file(self, mode: str = 'rt'):
        """
        Open file, handling both plain and gzipped files.
        
        Args:
            mode: File mode (default 'rt' for text reading)
            
        Returns:
            File handle
        """
        if self.filepath.suffix.lower() == '.gz':
            # Use gzip with UTF-8 encoding, ignore errors
            return gzip.open(self.filepath, mode, encoding='utf-8', errors='ignore')
        else:
            # Use regular open with UTF-8 encoding, ignore errors
            return open(self.filepath, mode, encoding='utf-8', errors='ignore')
    
    def _detect_format(self) -> str:
        """
        Detect file format (GTF or BED12).
        
        Returns:
            'gtf' or 'bed12'
        """
        # Check file extension (handle .gz files)
        filepath_str = str(self.filepath).lower()
        if '.gtf' in filepath_str or '.gff' in filepath_str:
            return 'gtf'
        elif '.bed' in filepath_str and '.bed12' not in filepath_str:
            # Default BED to bed12 if not clear
            return 'bed12'
        else:
            # Try to detect from content
            with self._open_file() as f:
                first_line = f.readline()
                if '\t' in first_line:
                    fields = first_line.split('\t')
                    if len(fields) >= 9 and ';' in first_line:
                        return 'gtf'
                    elif len(fields) >= 12:
                        return 'bed12'
        
        raise ValueError(f"Cannot detect file format for {self.filepath}")
    
    @staticmethod
    def _get_bin_size(window_size: int) -> int:
        """Return bin size (bp) for cache tier from window size."""
        if window_size > WINDOW_LARGE:
            return BIN_SIZE_LARGE
        if window_size > WINDOW_MEDIUM:
            return BIN_SIZE_MEDIUM
        return BIN_SIZE_SMALL
    
    def _ensure_bed12_index(self) -> None:
        """Build in-memory BED12 index by chrom (sorted by start). One-time load."""
        if self._bed12_index is not None:
            return
        index: Dict[str, List[Dict]] = defaultdict(list)
        with self._open_file() as f:
            for line in f:
                if line.startswith('#') or line.startswith('track'):
                    continue
                fields = line.strip().split('\t')
                if len(fields) < 12:
                    continue
                try:
                    chrom = fields[0]
                    start = int(fields[1])
                    end = int(fields[2])
                    name = fields[3]
                    strand = fields[5] if len(fields) > 5 else '+'
                    exon_count = int(fields[9])
                    exon_sizes = [int(x) for x in fields[10].rstrip(',').split(',')]
                    exon_starts = [int(x) for x in fields[11].rstrip(',').split(',')]
                    exons = []
                    for i in range(exon_count):
                        exons.append((start + exon_starts[i], start + exon_starts[i] + exon_sizes[i]))
                    index[chrom].append({
                        'name': name,
                        'chrom': chrom,
                        'start': start,
                        'end': end,
                        'strand': strand,
                        'exons': exons
                    })
                except (ValueError, IndexError):
                    continue
        for ch in index:
            index[ch].sort(key=lambda g: g['start'])
        self._bed12_index = dict(index)
    
    def _get_transcripts_for_region_bed12(
        self,
        chrom: str,
        start: int,
        end: int
    ) -> Tuple[List[Dict], int]:
        """
        Get transcripts overlapping [start, end] using bin cache.
        Cache key: (chrom, bin_id, bin_size). bin_size from window tier.
        Returns (list of transcript dicts, window_size).
        """
        self._ensure_bed12_index()
        window_size = end - start
        bin_size = self._get_bin_size(window_size)
        bin_start = start // bin_size
        bin_end = end // bin_size
        
        result: List[Dict] = []
        chrom_list = self._bed12_index.get(chrom)
        if not chrom_list:
            return [], window_size
        
        # Cache key: (genome/track id, chr, bin_id, bin_size)
        track_id = (str(self.filepath), self.name)
        for bin_id in range(bin_start, bin_end + 1):
            key = (track_id, chrom, bin_id, bin_size)
            if key not in self._bed12_cache:
                b_start = bin_id * bin_size
                b_end = (bin_id + 1) * bin_size
                # Binary-search style: first transcript with end > b_start
                bin_genes = []
                for g in chrom_list:
                    if g['end'] <= b_start:
                        continue
                    if g['start'] >= b_end:
                        break
                    bin_genes.append(g)
                self._bed12_cache[key] = bin_genes
            result.extend(self._bed12_cache[key])
        
        # Dedupe by (start, end, name) and filter to overlap [start, end]
        seen: set = set()
        filtered = []
        for g in result:
            if g['end'] <= start or g['start'] >= end:
                continue
            k = (g['start'], g['end'], g['name'])
            if k in seen:
                continue
            seen.add(k)
            filtered.append(g)
        return filtered, window_size
    
    def draw(self, ax: plt.Axes, region: Tuple[str, int, int]) -> None:
        """
        Draw gene annotations with exons, introns, and labels.
        
        For BED12: window-size strategy and bin-based cache.
        - window > 2 Mb: gene names only
        - 50 kb < window <= 2 Mb: gene-level line + strand arrow
        - window <= 50 kb: full BED12 exon blocks
        
        For GTF: full load, filter, layout, draw (unchanged).
        
        Args:
            ax: Matplotlib Axes to draw on
            region: Genomic region (chrom, start, end)
        """
        chrom, start, end = region
        
        try:
            file_format = self._detect_format()
            
            if file_format == 'bed12':
                genes, window_size = self._get_transcripts_for_region_bed12(chrom, start, end)
                genes = self._limit_genes(genes)
                
                if len(genes) == 0:
                    self._draw_empty(ax, "No genes in region")
                else:
                    if window_size > WINDOW_LARGE:
                        self._draw_genes_names_only(ax, genes, start, end)
                    elif window_size > WINDOW_MEDIUM:
                        gene_rows = self._layout_genes(genes)
                        self._draw_genes(ax, gene_rows, start, end, draw_exons=False)
                    else:
                        gene_rows = self._layout_genes(genes)
                        self._draw_genes(ax, gene_rows, start, end, draw_exons=True)
            else:
                # GTF path: load all, filter, layout, draw
                genes = self._get_filtered_genes(chrom, start, end)
                genes = self._limit_genes(genes)
                
                if len(genes) == 0:
                    self._draw_empty(ax, "No genes in region")
                else:
                    gene_rows = self._layout_genes(genes)
                    self._draw_genes(ax, gene_rows, start, end, draw_exons=True)
            
        except Exception as e:
            self._draw_empty(ax, f"Error loading genes:\n{str(e)}", color='red', fontsize=8)
        
        self.set_xlim(ax, start, end)
        self.format_axis(ax, show_xlabel=False)
    
    def _draw_empty(
        self,
        ax: plt.Axes,
        message: str,
        color: str = 'gray',
        fontsize: int = 9
    ) -> None:
        """Draw empty-state message on axis."""
        ax.text(
            0.5, 0.5, message,
            transform=ax.transAxes,
            ha='center', va='center',
            fontsize=fontsize, color=color
        )
        ax.set_ylim(0, 1)
    
    def _load_genes(self) -> Dict:
        """
        Load and parse gene file.
        
        Returns:
            Dictionary of gene structures
        """
        if self._genes is not None:
            return self._genes
        
        file_format = self._detect_format()
        
        if file_format == 'gtf':
            self._genes = self._parse_gtf()
        elif file_format == 'bed12':
            self._genes = self._parse_bed12()
        else:
            self._genes = {}
        
        return self._genes
    
    def _parse_gtf(self) -> Dict:
        """
        Parse GTF file into gene structures.
        
        Returns:
            Dict of {gene_id: {name, chrom, start, end, strand, exons: [(start, end)]}}
        """
        genes = {}
        
        with self._open_file() as f:
            for line in f:
                if line.startswith('#'):
                    continue
                
                fields = line.strip().split('\t')
                if len(fields) < 9:
                    continue
                
                feature_type = fields[2]
                
                # Only process exons for now (simplification)
                if feature_type not in ['exon', 'CDS']:
                    continue
                
                chrom = fields[0]
                feat_start = int(fields[3]) - 1  # GTF is 1-based
                feat_end = int(fields[4])
                strand = fields[6]
                
                # Parse attributes
                attrs = {}
                for attr in fields[8].split(';'):
                    attr = attr.strip()
                    if ' ' in attr:
                        key, value = attr.split(' ', 1)
                        attrs[key] = value.strip('"')
                
                gene_id = attrs.get('gene_id', '')
                gene_name = attrs.get('gene_name', gene_id)
                
                if not gene_id:
                    continue
                
                # Initialize gene if not seen
                if gene_id not in genes:
                    genes[gene_id] = {
                        'name': gene_name,
                        'chrom': chrom,
                        'start': feat_start,
                        'end': feat_end,
                        'strand': strand,
                        'exons': []
                    }
                else:
                    # Update gene boundaries
                    genes[gene_id]['start'] = min(genes[gene_id]['start'], feat_start)
                    genes[gene_id]['end'] = max(genes[gene_id]['end'], feat_end)
                
                # Add exon
                genes[gene_id]['exons'].append((feat_start, feat_end))
        
        return genes
    
    def _parse_bed12(self) -> Dict:
        """
        Parse BED12 file into gene structures.
        
        Returns:
            Dict of gene structures
        """
        genes = {}
        
        with self._open_file() as f:
            for line in f:
                if line.startswith('#') or line.startswith('track'):
                    continue
                
                fields = line.strip().split('\t')
                if len(fields) < 12:
                    continue
                
                try:
                    chrom = fields[0]
                    start = int(fields[1])
                    end = int(fields[2])
                    name = fields[3]
                    strand = fields[5] if len(fields) > 5 else '+'
                    exon_count = int(fields[9])
                    exon_sizes = [int(x) for x in fields[10].rstrip(',').split(',')]
                    exon_starts = [int(x) for x in fields[11].rstrip(',').split(',')]
                    
                    # Build exon coordinates
                    exons = []
                    for i in range(exon_count):
                        exon_start = start + exon_starts[i]
                        exon_end = exon_start + exon_sizes[i]
                        exons.append((exon_start, exon_end))
                    
                    gene_id = f"{chrom}:{start}-{end}:{name}"
                    genes[gene_id] = {
                        'name': name,
                        'chrom': chrom,
                        'start': start,
                        'end': end,
                        'strand': strand,
                        'exons': exons
                    }
                
                except (ValueError, IndexError):
                    continue
        
        return genes
    
    def _get_filtered_genes(
        self, 
        chrom: str, 
        start: int, 
        end: int
    ) -> List[Dict]:
        """
        Get genes that overlap with the region.
        
        Args:
            chrom: Chromosome name
            start: Region start
            end: Region end
            
        Returns:
            List of gene dictionaries
        """
        all_genes = self._load_genes()
        
        filtered = []
        for gene_id, gene_data in all_genes.items():
            # Check chromosome and overlap
            if gene_data['chrom'] != chrom:
                continue
            
            if gene_data['end'] <= start or gene_data['start'] >= end:
                continue
            
            filtered.append(gene_data)
        
        return filtered
    
    @staticmethod
    def _gene_display_name(gene: Dict) -> str:
        """Return gene name for display: only the part before '|' (e.g. FAM87B from FAM87B|ENST00000326734.2)."""
        name = gene.get('name') or ''
        return name.split('|')[0].strip() if name else ''
    
    def _limit_genes(self, genes: List[Dict]) -> List[Dict]:
        """
        Limit to at most max_genes, chosen randomly. When query_gene is set,
        that gene is always included (matched by display name, case-insensitive);
        the remaining slots are filled by random choice from other genes.
        
        Args:
            genes: List of gene dictionaries (overlapping the region)
            
        Returns:
            Subset of genes, at most max_genes, with query_gene included if set
        """
        if len(genes) <= self.max_genes and not self.query_gene:
            return genes
        
        q = (self.query_gene or "").strip().lower()
        if not q:
            return random.sample(genes, min(len(genes), self.max_genes))
        
        # Always include genes matching query_gene (by display name, e.g. FAM87B)
        matching = [g for g in genes if self._gene_display_name(g).lower() == q]
        others = [g for g in genes if self._gene_display_name(g).lower() != q]
        n_extra = self.max_genes - len(matching)
        if n_extra <= 0:
            return matching[:self.max_genes]
        # Randomly sample from others to fill remaining slots
        result = matching[:]
        result.extend(random.sample(others, min(n_extra, len(others))))
        return result
    
    def _layout_genes(self, genes: List[Dict]) -> List[List[Dict]]:
        """
        Layout genes in rows to avoid overlaps.
        
        Expanded: greedy algorithm, place each gene in the first available row
                  where it doesn't overlap with any existing gene.
        Condensed: all genes in a single row (may overlap).
        
        Args:
            genes: List of gene dictionaries
            
        Returns:
            List of rows, where each row is a list of genes (no overlaps within each row)
        """
        sorted_genes = sorted(genes, key=lambda g: g['start'])
        
        if self.layout_mode == "condensed":
            return [sorted_genes]
        
        rows = []
        for gene in sorted_genes:
            placed = False
            # Try to place gene in an existing row
            for row in rows:
                # Check if gene overlaps with any gene in this row
                overlaps = False
                for existing_gene in row:
                    # Two genes overlap if neither is completely before the other
                    if not (gene['end'] <= existing_gene['start'] or existing_gene['end'] <= gene['start']):
                        overlaps = True
                        break
                
                if not overlaps:
                    row.append(gene)
                    placed = True
                    break
            
            # If couldn't place in any existing row, create a new row (if under max_rows)
            if not placed:
                if len(rows) < self.max_rows:
                    rows.append([gene])
                # If max_rows reached, skip this gene (or could use condensed mode for overflow)
        return rows
    
    def _draw_genes_names_only(
        self,
        ax: plt.Axes,
        genes: List[Dict],
        region_start: int,
        region_end: int
    ) -> None:
        """Draw only gene names (window > 2 Mb). No exons, no lines. Shows gene name only (e.g. FAM87B, not transcript id)."""
        ax.set_ylim(0, 1)
        y = 0.5
        for g in genes:
            mid = (max(g['start'], region_start) + min(g['end'], region_end)) / 2
            name = self._gene_display_name(g)
            if not name:
                continue
            ax.text(
                mid, y, name,
                fontsize=self.gene_fontsize,
                ha='center', va='center',
                style='italic',
                color='black'
            )
        ax.set_yticks([])
    
    def _draw_genes(
        self, 
        ax: plt.Axes, 
        gene_rows: List[List[Dict]],
        region_start: int,
        region_end: int,
        draw_exons: bool = True
    ) -> None:
        """
        Draw genes with optional exons and introns.
        
        Args:
            ax: Matplotlib Axes
            gene_rows: List of gene rows
            region_start: Region start position
            region_end: Region end position
            draw_exons: If False, draw only gene line + strand arrow + name (50 kb–2 Mb mode)
        """
        n_rows = len(gene_rows)
        
        if n_rows == 0:
            return
        
        # Set y-limits
        ax.set_ylim(-0.5, n_rows)
        
        # Draw each row
        for row_idx, row_genes in enumerate(gene_rows):
            y_center = row_idx + 0.5
            
            for gene in row_genes:
                self._draw_single_gene(
                    ax, gene, y_center, region_start, region_end, draw_exons=draw_exons
                )
        
        # Remove y-axis ticks
        ax.set_yticks([])
    
    def _draw_single_gene(
        self, 
        ax: plt.Axes, 
        gene: Dict,
        y_center: float,
        region_start: int,
        region_end: int,
        draw_exons: bool = True
    ) -> None:
        """
        Draw a single gene with exons (optional), introns, and label.
        
        Args:
            ax: Matplotlib Axes
            gene: Gene dictionary
            y_center: Y-coordinate for gene center
            region_start: Region start
            region_end: Region end
            draw_exons: If False, only draw gene line + strand arrow + name (no exon blocks)
        """
        # Clip gene to region
        gene_start = max(gene['start'], region_start)
        gene_end = min(gene['end'], region_end)
        
        # Condensed mode: smaller glyphs; label font uses self.gene_fontsize
        if self.layout_mode == "condensed":
            intron_h, exon_h, lw = 0.08, 0.25, 0.5
        else:
            intron_h, exon_h, lw = self.intron_height, self.exon_height, 1.0
        
        # Draw gene body (intron line)
        ax.plot(
            [gene_start, gene_end],
            [y_center, y_center],
            color=self.gene_color,
            linewidth=lw,
            alpha=0.7,
            solid_capstyle='butt'
        )
        
        # Draw exons (only when draw_exons=True, e.g. window <= 50 kb)
        if draw_exons and gene.get('exons'):
            for exon_start, exon_end in gene['exons']:
                exon_start = max(exon_start, region_start)
                exon_end = min(exon_end, region_end)
                if exon_start >= exon_end:
                    continue
                rect = mpatches.Rectangle(
                    (exon_start, y_center - exon_h / 2),
                    exon_end - exon_start,
                    exon_h,
                    facecolor=self.exon_color,
                    edgecolor='none',
                    alpha=0.8
                )
                ax.add_patch(rect)
        
        # Draw strand arrow
        self._draw_strand_arrow(ax, gene_start, gene_end, y_center, gene['strand'], lw)
        
        # Add gene name label (display name only, e.g. FAM87B not FAM87B|ENST00000326734.2)
        display_name = self._gene_display_name(gene)
        if self.show_gene_names and display_name:
            ax.text(
                gene_start,
                y_center + exon_h,
                display_name,
                fontsize=self.gene_fontsize,
                ha='left',
                va='bottom',
                style='italic',
                color='black'
            )
    
    def _draw_strand_arrow(
        self, 
        ax: plt.Axes, 
        start: int, 
        end: int, 
        y: float, 
        strand: str,
        linewidth: float = 1.0
    ) -> None:
        """
        Draw small arrow to indicate strand direction.
        
        Args:
            ax: Matplotlib Axes
            start: Gene start
            end: Gene end
            y: Y-coordinate
            strand: Strand ('+' or '-')
            linewidth: Arrow line width
        """
        mid = (start + end) / 2
        arrow_size = (end - start) * 0.05
        
        if strand == '+':
            # Right-pointing arrow
            ax.annotate(
                '',
                xy=(mid + arrow_size, y),
                xytext=(mid - arrow_size, y),
                arrowprops=dict(
                    arrowstyle='->',
                    color=self.gene_color,
                    lw=linewidth
                )
            )
        elif strand == '-':
            ax.annotate(
                '',
                xy=(mid - arrow_size, y),
                xytext=(mid + arrow_size, y),
                arrowprops=dict(
                    arrowstyle='->',
                    color=self.gene_color,
                    lw=linewidth
                )
            )

