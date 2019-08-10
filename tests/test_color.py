"""Test for color conversion."""
import numpy as np
from wasabi2d.color import convert_color


def test_color_name():
    """Convert from a color name to an np.array."""
    assert np.array_equal(
        convert_color('black'),
        np.array([0, 0, 0, 1], dtype='f4')
    )


def test_color_3tuple():
    """Convert from a 3-tuple to an np.array."""
    assert np.array_equal(
        convert_color((0, 0, 1)),
        np.array([0, 0, 1, 1], dtype='f4')
    )
