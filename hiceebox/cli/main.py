"""Main CLI entry point for HiCeeBox."""

import argparse
import sys
from pathlib import Path

from hiceebox.utils.config import load_config
from hiceebox import __version__


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='hiceebox',
        description='HiCeeBox: Hi-C + multi-omics visualization toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a plot from configuration file
  hiceebox plot --config config.yaml --output figure.pdf
  
  # Display plot interactively
  hiceebox plot --config config.yaml --show
  
  # High-resolution PNG output
  hiceebox plot --config config.yaml --output figure.png --dpi 600

For more information, visit: https://github.com/yourusername/hiceebox
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'HiCeeBox {__version__}'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Plot command
    plot_parser = subparsers.add_parser(
        'plot',
        help='Generate genomic visualization from config file'
    )
    
    plot_parser.add_argument(
        '--config', '-c',
        required=True,
        type=str,
        help='Path to YAML configuration file'
    )
    
    plot_parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (PDF, PNG, or SVG)'
    )
    
    plot_parser.add_argument(
        '--show',
        action='store_true',
        help='Display plot interactively'
    )
    
    plot_parser.add_argument(
        '--dpi',
        type=int,
        help='Override DPI setting from config'
    )
    
    plot_parser.add_argument(
        '--width',
        type=float,
        help='Override figure width from config (inches)'
    )
    
    # gtf2bed12: preprocess GTF to BED12 (by transcript)
    gtf2bed_parser = subparsers.add_parser(
        'gtf2bed12',
        help='Convert GTF to BED12 (one row per transcript) for fast gene track loading'
    )
    gtf2bed_parser.add_argument(
        'gtf',
        type=str,
        help='Input GTF or GTF.GZ file'
    )
    gtf2bed_parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Output BED12 path (.gz allowed)'
    )
    gtf2bed_parser.add_argument(
        '--cds',
        action='store_true',
        help='Use CDS range for thickStart/thickEnd; default is txStart/txStart'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'plot':
        plot_command(args)
    elif args.command == 'gtf2bed12':
        gtf2bed12_command(args)


def plot_command(args):
    """
    Execute the plot command.
    
    Args:
        args: Parsed command-line arguments
    """
    try:
        # Load configuration
        print(f"Loading configuration from: {args.config}")
        view = load_config(args.config)
        
        # Override settings if provided
        if args.dpi:
            view.dpi = args.dpi
        
        if args.width:
            view.width = args.width
        
        # Display configuration info
        print(f"Region: {view.chrom}:{view.start:,}-{view.end:,} ({view.region_size:,} bp)")
        print(f"Tracks: {len(view.tracks)}")
        for i, track in enumerate(view.tracks, 1):
            print(f"  {i}. {track.__class__.__name__}: {track.name}")
        
        # Generate plot
        print("Generating plot...")
        view.plot(output=args.output, show=args.show)
        
        if args.output:
            print(f"✓ Successfully saved to: {args.output}")
        
        if args.show:
            print("✓ Displaying plot")
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def gtf2bed12_command(args):
    """Run GTF to BED12 conversion."""
    from hiceebox.utils.gtf_to_bed12 import gtf_to_bed12
    try:
        n = gtf_to_bed12(args.gtf, args.output, use_cds=args.cds)
        print(f"Wrote {n} transcripts to {args.output}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

