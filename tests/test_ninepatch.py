"""Tests for scalable nine-patch panels."""
import numpy as np
import pytest

import wasabi2d as w2d

from drawing_utils import drawing_test


TILE_PATCH = w2d.NinePatch('tile', hcuts=(8, 24), vcuts=(8, 24))


@drawing_test
def test_draw_ninepatch(scene):
    """Nine-patches preserve their borders at different sizes."""
    layer = scene.layers[0]
    layer.add_ninepatch(TILE_PATCH, pos=(170, 170), width=260, height=90)
    layer.add_ninepatch(
        TILE_PATCH,
        pos=(570, 170),
        width=90,
        height=260,
        angle=0.2,
        color='#b8d8ff',
    )
    layer.add_ninepatch(TILE_PATCH, pos=(400, 440), width=10, height=10)


def test_ninepatch_can_resize_and_delete(scene):
    """Resizing dirties the primitive and deletion releases its allocation."""
    primitive = scene.layers[0].add_ninepatch(
        TILE_PATCH,
        pos=(100, 80),
        width=80,
        height=40,
    )
    scene.draw(0, 0, True)

    verts = primitive._array.get_verts(primitive._array_id)['in_vert']
    assert np.allclose(verts.min(axis=0), (60, 60))
    assert np.allclose(verts.max(axis=0), (140, 100))

    primitive.width = 120
    primitive.height = 60
    assert primitive in primitive.layer._dirty

    array = primitive._array
    primitive.patch = w2d.NinePatch('tile', (6, 26), (6, 26))
    assert primitive._array is array
    assert len(array.allocs) == 1

    primitive.delete()
    assert not primitive.is_alive()
    assert not array.allocs


@pytest.mark.parametrize(
    'patch',
    [
        w2d.NinePatch('tile', (-1, 12), (4, 12)),
        w2d.NinePatch('tile', (12, 4), (4, 12)),
        w2d.NinePatch('tile', (4, 1000), (4, 12)),
    ],
)
def test_ninepatch_rejects_invalid_cuts(scene, patch):
    """Cut coordinates must be ordered and within the source image."""
    with pytest.raises(ValueError):
        scene.layers[0].add_ninepatch(patch)
