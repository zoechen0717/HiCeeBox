"""Test that all modules can be imported successfully."""

import pytest


def test_import_main_package():
    """Test importing main package."""
    import hiceebox
    assert hiceebox.__version__ == "0.1.0"


def test_import_matrix_providers():
    """Test importing matrix provider classes."""
    from hiceebox.matrix import MatrixProvider, CoolerMatrixProvider, HicMatrixProvider
    assert MatrixProvider is not None
    assert CoolerMatrixProvider is not None
    assert HicMatrixProvider is not None


def test_import_tracks():
    """Test importing track classes."""
    from hiceebox.tracks import (
        Track,
        HiCTriangleTrack,
        BigWigTrack,
        BedTrack,
        BedPETrack,
        GeneTrack
    )
    assert Track is not None
    assert HiCTriangleTrack is not None
    assert BigWigTrack is not None
    assert BedTrack is not None
    assert BedPETrack is not None
    assert GeneTrack is not None


def test_import_view():
    """Test importing view classes."""
    from hiceebox.view import GenomeView, LayoutManager
    assert GenomeView is not None
    assert LayoutManager is not None


def test_import_utils():
    """Test importing utility functions."""
    from hiceebox.utils import load_config, parse_region, format_position
    from hiceebox.utils import get_colormap, validate_color
    assert load_config is not None
    assert parse_region is not None
    assert format_position is not None
    assert get_colormap is not None
    assert validate_color is not None


def test_import_cli():
    """Test importing CLI."""
    from hiceebox.cli import main
    assert main is not None


def test_top_level_imports():
    """Test top-level package imports."""
    from hiceebox import GenomeView, MatrixProvider, Track
    assert GenomeView is not None
    assert MatrixProvider is not None
    assert Track is not None

