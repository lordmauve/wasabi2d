"""Regression tests for tile maps."""
from drawing_utils import drawing_test


@drawing_test
def test_tilemap_tile(scene):
    """We can draw tiles in the scene."""
    tm = scene.layers[0].add_tile_map()
    tm[3, 3] = 'tile'
    tm[5, 7] = 'bomb'


@drawing_test
def test_tilemap_fill_rect(scene):
    """We can fill a whole rectangle of tiles."""
    tilemap = scene.layers[0].add_tile_map()
    tilemap.fill_rect('tile', 3, 6, 6, 9)
