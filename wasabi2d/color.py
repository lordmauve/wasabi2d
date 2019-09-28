"""Color conversion functions."""
from typing import Union, Tuple
import numpy as np
from pygame import Color


def convert_color(c: Union[str, tuple]) -> Tuple[float, float, float, float]:
    """Convert a color to an RGBA tuple."""
    if isinstance(c, str):
        try:
            col = Color(c)
        except ValueError:
            if c.startswith('#'):
                raise ValueError(f"Malformed hex color {c!r}") from None
            raise
        return np.array(memoryview(col), dtype='u1').astype('f4') / 255.0
    else:
        assert 3 <= len(c) <= 4, "Invalid color length"
        return np.array(c + (1,) * (4 - len(c)), dtype='f4')


def convert_color_rgb(c: Union[str, tuple]) -> Tuple[float, float, float]:
    """Convert a color to an RGB tuple.

    This accepts the same input formats as convert_color, but raises an
    exception if the alpha value is not 1.

    """
    c = convert_color(c)
    if abs(c[3] - 1.0) > 1e-4:
        raise ValueError("Color may not have an alpha component.")
    return c[:3]
