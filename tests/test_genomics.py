"""Tests for genomics utility functions."""

import pytest
from hiceebox.utils.genomics import (
    parse_region,
    format_position,
    format_region,
    get_region_size,
    overlap,
    contains,
    clamp
)


def test_parse_region_basic():
    """Test basic region parsing."""
    chrom, start, end = parse_region("chr1:1000-2000")
    assert chrom == "chr1"
    assert start == 1000
    assert end == 2000


def test_parse_region_with_commas():
    """Test parsing regions with comma separators."""
    chrom, start, end = parse_region("chr6:30,000,000-32,000,000")
    assert chrom == "chr6"
    assert start == 30_000_000
    assert end == 32_000_000


def test_parse_region_invalid():
    """Test that invalid regions raise errors."""
    with pytest.raises(ValueError):
        parse_region("invalid")
    
    with pytest.raises(ValueError):
        parse_region("chr1:2000-1000")  # start >= end


def test_format_position():
    """Test position formatting."""
    assert format_position(1000) == "1,000"
    assert format_position(1_000_000) == "1,000,000"
    assert format_position(30_000_000) == "30,000,000"


def test_format_region():
    """Test region formatting."""
    result = format_region("chr6", 30_000_000, 32_000_000)
    assert result == "chr6:30,000,000-32,000,000"


def test_get_region_size():
    """Test region size calculation."""
    assert get_region_size(1000, 2000) == 1000
    assert get_region_size(30_000_000, 32_000_000) == 2_000_000


def test_overlap():
    """Test interval overlap calculation."""
    # Overlapping intervals
    result = overlap(100, 200, 150, 250)
    assert result == (150, 200)
    
    # Non-overlapping intervals
    result = overlap(100, 200, 300, 400)
    assert result is None
    
    # Contained interval
    result = overlap(100, 300, 150, 200)
    assert result == (150, 200)


def test_contains():
    """Test interval containment."""
    assert contains(100, 300, 150, 200) is True
    assert contains(100, 300, 50, 400) is False
    assert contains(100, 300, 100, 300) is True


def test_clamp():
    """Test value clamping."""
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10

