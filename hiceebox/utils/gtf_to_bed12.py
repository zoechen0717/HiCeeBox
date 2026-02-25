"""
Convert GTF to BED12 by transcript for fast gene track loading.

Preprocess once from the command line, then use the resulting BED12 in the app:
  hiceebox gtf2bed12 genes.gtf.gz -o genes.bed12

BED12 fields (per transcript):
  chrom, txStart, txEnd, name=gene_name|transcript_id, score=0, strand,
  thickStart, thickEnd, itemRgb, blockCount, blockSizes, blockStarts
"""

from pathlib import Path
from collections import defaultdict
import gzip


def _open_gtf(path: Path, mode: str = "rt"):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, mode, encoding="utf-8", errors="ignore")
    return open(path, mode, encoding="utf-8", errors="ignore")


def _parse_attrs(attr_str: str) -> dict:
    attrs = {}
    for part in attr_str.split(";"):
        part = part.strip()
        if " " in part:
            k, v = part.split(" ", 1)
            attrs[k] = v.strip('"')
    return attrs


def gtf_to_bed12(
    gtf_path: str,
    out_path: str,
    use_cds: bool = False,
    name_format: str = "gene_name|transcript_id",
) -> int:
    """
    Convert GTF to BED12 (one row per transcript).

    Transcript-level fields:
      txStart = min(exon start)
      txEnd = max(exon end)
      name = gene_name|transcript_id (or custom format)
      score = 0
      strand = +/-
      thickStart/thickEnd = txStart/txEnd if not use_cds else CDS span
      blockCount, blockSizes, blockStarts from exons (sorted by start)

    Args:
        gtf_path: Input GTF or GTF.GZ path
        out_path: Output BED12 path (.gz allowed)
        use_cds: If True, set thickStart/thickEnd to CDS span; else use tx
        name_format: Format for name: "gene_name|transcript_id" or "gene_id|transcript_id"

    Returns:
        Number of BED12 rows (transcripts) written.
    """
    gtf_path = Path(gtf_path)
    out_path = Path(out_path)
    if not gtf_path.exists():
        raise FileNotFoundError(gtf_path)

    # By transcript_id: list of (start, end) for exons, and optional CDS
    transcripts = defaultdict(lambda: {
        "chrom": None,
        "strand": "+",
        "gene_id": "",
        "gene_name": "",
        "transcript_id": "",
        "exons": [],  # (start, end) 0-based
        "cds": None,  # (start, end) or None
    })

    with _open_gtf(gtf_path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            fields = line.strip().split("\t")
            if len(fields) < 9:
                continue
            feature = fields[2]
            chrom = fields[0]
            start = int(fields[3]) - 1  # 1-based -> 0-based
            end = int(fields[4])
            strand = fields[6] if len(fields) > 6 else "+"
            attrs = _parse_attrs(fields[8])
            tid = attrs.get("transcript_id") or attrs.get("gene_id")
            if not tid:
                continue
            t = transcripts[tid]
            t["chrom"] = chrom
            t["strand"] = strand
            t["gene_id"] = attrs.get("gene_id", "")
            t["gene_name"] = attrs.get("gene_name", t["gene_id"])
            t["transcript_id"] = tid

            if feature == "exon":
                t["exons"].append((start, end))
            elif feature == "CDS" and use_cds:
                if t["cds"] is None:
                    t["cds"] = (start, end)
                else:
                    t["cds"] = (min(t["cds"][0], start), max(t["cds"][1], end))

    # Build and sort exons per transcript; skip transcripts with no exons
    rows = []
    for tid, t in transcripts.items():
        exons = t["exons"]
        if not exons:
            continue
        exons = sorted(exons, key=lambda e: e[0])
        tx_start = min(e[0] for e in exons)
        tx_end = max(e[1] for e in exons)
        rows.append((tid, t, exons, tx_start, tx_end))
    rows.sort(key=lambda r: (r[1]["chrom"] or "", r[3]))

    n_written = 0
    out_gz = out_path.suffix.lower() == ".gz"
    open_out = gzip.open(out_path, "wt", encoding="utf-8") if out_gz else open(out_path, "w", encoding="utf-8")

    with open_out as out:
        for tid, t, exons, tx_start, tx_end in rows:
            if use_cds and t["cds"] is not None:
                thick_start, thick_end = t["cds"]
            else:
                thick_start, thick_end = tx_start, tx_start  # or tx_start, tx_end
            name = name_format.replace("gene_name", t["gene_name"]).replace("gene_id", t["gene_id"]).replace("transcript_id", tid)
            block_count = len(exons)
            block_sizes = ",".join(str(e[1] - e[0]) for e in exons)
            block_starts = ",".join(str(e[0] - tx_start) for e in exons)
            # BED12: chrom, chromStart, chromEnd, name, score, strand, thickStart, thickEnd, itemRgb, blockCount, blockSizes, blockStarts
            bed = [
                t["chrom"],
                str(tx_start),
                str(tx_end),
                name,
                "0",
                t["strand"],
                str(thick_start),
                str(thick_end),
                "0",
                str(block_count),
                block_sizes,
                block_starts,
            ]
            out.write("\t".join(bed) + "\n")
            n_written += 1

    return n_written
