"""Color utilities for visualization."""

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from typing import Union, Optional


def get_colormap(name: str, n_colors: Optional[int] = None):
    """
    Get matplotlib colormap by name.
    
    Args:
        name: Colormap name (e.g., 'Reds', 'viridis', 'RdBu_r')
        n_colors: Optional number of discrete colors
        
    Returns:
        Matplotlib colormap object
    """
    try:
        cmap = plt.get_cmap(name)
    except ValueError:
        raise ValueError(f"Unknown colormap: {name}")
    
    if n_colors is not None:
        cmap = plt.get_cmap(name, n_colors)
    
    return cmap


def validate_color(color: Union[str, tuple]) -> bool:
    """
    Validate if a color specification is valid.
    
    Args:
        color: Color name, hex string, or RGB tuple
        
    Returns:
        True if valid color
    """
    try:
        mcolors.to_rgba(color)
        return True
    except (ValueError, TypeError):
        return False


def hex_to_rgb(hex_color: str) -> tuple:
    """
    Convert hex color to RGB tuple.
    
    Args:
        hex_color: Hex color string (e.g., '#FF0000' or 'FF0000')
        
    Returns:
        RGB tuple (r, g, b) with values 0-1
    """
    hex_color = hex_color.lstrip('#')
    
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    
    return (r, g, b)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    """
    Convert RGB tuple to hex color string.
    
    Args:
        r: Red value (0-1)
        g: Green value (0-1)
        b: Blue value (0-1)
        
    Returns:
        Hex color string (e.g., '#FF0000')
    """
    r_int = int(r * 255)
    g_int = int(g * 255)
    b_int = int(b * 255)
    
    return f"#{r_int:02X}{g_int:02X}{b_int:02X}"


def lighten_color(color: Union[str, tuple], amount: float = 0.5) -> tuple:
    """
    Lighten a color by blending with white.
    
    Args:
        color: Color specification
        amount: Amount to lighten (0-1, where 1 is white)
        
    Returns:
        Lightened RGB tuple
    """
    import matplotlib.colors as mc
    import colorsys
    
    try:
        c = mc.cnames[color]
    except KeyError:
        c = color
    
    c = colorsys.rgb_to_hls(*mc.to_rgb(c))
    rgb = colorsys.hls_to_rgb(c[0], 1 - amount * (1 - c[1]), c[2])
    
    return rgb


def darken_color(color: Union[str, tuple], amount: float = 0.5) -> tuple:
    """
    Darken a color by blending with black.
    
    Args:
        color: Color specification
        amount: Amount to darken (0-1, where 1 is black)
        
    Returns:
        Darkened RGB tuple
    """
    import matplotlib.colors as mc
    import colorsys
    
    try:
        c = mc.cnames[color]
    except KeyError:
        c = color
    
    c = colorsys.rgb_to_hls(*mc.to_rgb(c))
    rgb = colorsys.hls_to_rgb(c[0], (1 - amount) * c[1], c[2])
    
    return rgb


# Predefined color palettes
PALETTE_CATEGORICAL = [
    '#E69F00',  # Orange
    '#56B4E9',  # Sky blue
    '#009E73',  # Green
    '#F0E442',  # Yellow
    '#0072B2',  # Blue
    '#D55E00',  # Vermillion
    '#CC79A7',  # Pink
]

PALETTE_SEQUENTIAL_BLUE = [
    '#EFF3FF',
    '#C6DBEF',
    '#9ECAE1',
    '#6BAED6',
    '#4292C6',
    '#2171B5',
    '#084594',
]

PALETTE_DIVERGING = [
    '#CA0020',  # Red
    '#F4A582',  # Light red
    '#F7F7F7',  # White
    '#92C5DE',  # Light blue
    '#0571B0',  # Blue
]

