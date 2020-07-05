"""Tests for grouping of primitives."""
import numpy as np
from pytest import approx

from wasabi2d.primitives.base import Transformable
from wasabi2d.primitives.group import Group


class Prim(Transformable):
    """A simple transformable primitive that can be queried for positions."""
    dirty = False

    def __init__(self, **kwargs):
        """Construct the object and set any of its attributes."""
        super().__init__()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def transformed_pos(self, pos):
        """Get the world position of a primitive coordinate."""
        vec = np.ones(3)
        vec[:2] = pos
        xformed = vec @ self._xform()
        return tuple(xformed[:2])

    def _set_dirty(self):
        """Dirtiness tracking is required by the Transformable interface."""
        self.dirty = True


def test_group():
    """We can group a primitive and move the group."""
    group = Group(
        [Prim(pos=(1, 1))],
        pos=(1, 1)
    )
    assert group[0].transformed_pos((1, 1)) == (3, 3)


def test_group_scale():
    """We can group a primitive and scale the group."""
    group = Group(
        [Prim(pos=(1, 1))],
        scale=2
    )
    assert group[0].transformed_pos((1, 1)) == (4, 4)


HALFPI = np.pi / 2
QPI = np.pi / 4


def test_group_rotate():
    """We can group a primitive and rotate the group."""
    group = Group(
        [Prim(angle=HALFPI)],
        angle=HALFPI
    )
    assert group[0].transformed_pos((1, 0)) == approx((-1, 0))


def test_group_pop():
    """Extracting a primitive from the group keeps its transformation."""
    group = Group(
        [Prim(pos=(1, 0), angle=QPI)],
        angle=QPI,
        pos=(10, 3),
        scale=2,
    )
    mat_before = group[0]._xform().copy()
    obj = group.pop(0)
    mat_after = obj._xform()
    assert mat_after == approx(mat_before)


def test_group_pop_props():
    """Extracting a primitive from the group sets its transform properties."""
    group = Group(
        [Prim(pos=(1, 0), angle=QPI)],
        angle=QPI,
        pos=(10, 3),
        scale=2,
    )
    obj = group.pop(0)

    root_half = 0.5 ** 0.5
    x = 10 + 2 * root_half
    y = 3 + 2 * root_half
    expected = (2, HALFPI, x, y)

    xform = (obj.scale, obj.angle, *obj.pos)
    assert xform == approx(expected)


def test_group_capture():
    """Capturing a primitive into the group keeps its transformation."""
    prim = Prim(pos=(1, 0), angle=QPI)
    group = Group(
        [],
        angle=QPI,
        pos=(10, 3),
        scale=2,
    )
    mat_before = prim._xform().copy()
    group.capture(prim)
    mat_after = prim._xform()
    assert mat_after == approx(mat_before, abs=1e-6), \
        f"Diff: {mat_after - mat_before!r}"


def test_group_capture_props():
    """Capturing a primitive into the group updates transform properties."""
    prim = Prim(pos=(2, 0))
    group = Group(
        [],
        pos=(10, 3),
    )
    group.scale_x = 0.5
    group.capture(prim)

    xform = (prim.scale_x, prim.scale_y, *prim.pos)
    expected = (2, 1, -16, -3)

    assert xform == approx(expected)
