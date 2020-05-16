"""Regression tests for tile maps."""
from pytest import fixture

from drawing_utils import drawing_test


@drawing_test
def test_tilemap_tile(scene):
    """We can draw tiles in the scene."""
    tm = scene.layers[0].add_tile_map()
    tm[3, 3] = 'tile'
    tm[5, 7] = 'bomb'


def test_tilemap_getitem(tilemap):
    """We can get the value of a tile we previously set."""
    tilemap[3, 3] = 'tile'
    assert tilemap[3, 3] == 'tile'


def test_tilemap_get(tilemap):
    """We can get tiles that may not be set."""
    tilemap[3, 3] = 'tile'
    assert tilemap.get((3, 3)) == 'tile'


def test_tilemap_get_none(tilemap):
    """We can get tiles that are not be set."""
    assert tilemap.get((3, 3)) == None


@drawing_test
def test_tilemap_fill_rect(scene):
    """We can fill a whole rectangle of tiles."""
    tilemap = scene.layers[0].add_tile_map()
    tilemap.fill_rect('tile', 3, 6, 6, 9)


@drawing_test
def test_tilemap_del(scene):
    """We can delete tiles."""
    tilemap = scene.layers[0].add_tile_map()
    tilemap.fill_rect('tile', 3, 6, 6, 9)

    del tilemap[4, 7]
    del tilemap[5, 7]
