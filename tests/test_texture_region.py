"""Test for subdividing a texture region."""
from unittest.mock import Mock
from pytest import approx, fixture

import numpy as np
from pygame import Rect
from wasabi2d.atlas import TextureRegion


@fixture()
def texregion():
    """Create a mock texture region."""
    tex = Mock(width=512, height=512)
    region = TextureRegion.for_tex(tex)
    return region


def test_subregion(texregion):
    """We can get a subregion of a region."""
    sub = TextureRegion.for_rect(texregion, Rect(10, 20, 32, 32))
    expected = np.array([
        (10, 52),
        (42, 52),
        (42, 20),
        (10, 20),
    ])
    assert sub.texcoords == approx(expected)
    assert sub.absregion() == Rect(10, 20, 32, 32)


def test_sub_subregion(texregion):
    """We can get a subregion of a region."""
    sub = TextureRegion.for_rect(texregion, Rect(10, 20, 32, 32))
    subsub = TextureRegion.for_rect(sub, Rect(5, 7, 16, 16))
    assert subsub.absregion() == Rect(15, 27, 16, 16)
    expected = np.array([
        (15, 43),
        (31, 43),
        (31, 27),
        (15, 27),
    ])
    assert subsub.texcoords == approx(expected)


def test_rotated_subregion(texregion):
    """We can rotate a subregion."""
    subrect = Rect(10, 20, 32, 32)
    sub = TextureRegion.for_rect(texregion, subrect).rotated()
    assert sub.absregion() == subrect
    expected = np.array([
        (42, 52),
        (42, 20),
        (10, 20),
        (10, 52),
    ])
    assert sub.texcoords == approx(expected)


def test_subregion_rotated_subregion(texregion):
    """We can get a subregion of a rotated subregion."""
    sub = TextureRegion.for_rect(texregion, Rect(10, 20, 32, 32)).rotated()
    subsub = TextureRegion.for_rect(sub, Rect(2, 3, 16, 16))
    assert subsub.absregion() == Rect(13, 34, 16, 16)
    expected = np.array([
        (29, 50),
        (29, 34),
        (13, 34),
        (13, 50),
    ])
    assert subsub.texcoords == approx(expected)
