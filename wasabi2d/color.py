"""Color conversion functions."""
from typing import Union, Tuple
import numpy as np
from pygame import Color


def convert_color(c: Union[str, tuple]) -> Tuple[float, float, float, float]:
    """Convert a color to an RGBA tuple."""
    if isinstance(c, str):
        col = Color(c)
        return np.array(memoryview(col), dtype='u1').astype('f4') / 255.0
    else:
        assert 3 <= len(c) <= 4, "Invalid color length"
        return np.array(c + (1,) * (4 - len(c)), dtype='f4')
