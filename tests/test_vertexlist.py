"""Test for managing vertex lists within VBOs."""
import numpy as np

from wasabi2d.allocators.vertlists import dtype_to_moderngl


def test_convert_structured_dtype():
    """We can convert a structured dtype to moderngl."""
    dt = np.dtype([('vert', '3f4'), ('color', '3u1')])
    assert dtype_to_moderngl(dt) == ('3f4 3f1', 'vert', 'color')


def test_convert_alignment():
    """We can convert a structured dtype with alignment."""
    dt = np.dtype('3u1,4f', align=True)
    assert dtype_to_moderngl(dt) == ('3f1 x 4f4', 'f0', 'f1')
