"""Regression tests for shader effects.

For all tests we compare rendering to a reference image generated with a
previous version of the software. We expect near pixel-perfect output, allowing
for variations in calculation accuracy.

"""
from drawing_utils import drawing_test, grid_coords


@drawing_test
def test_sepia(scene):
    """We can convert an image to sepia."""
    coords = grid_coords((2, 2), (scene.width, scene.height))
    for i, pos in enumerate(coords, start=1):
        photo = scene.layers[i].add_sprite('positano', pos=pos)
        photo.scale = min(
            (scene.width / 2 - 8) / photo.width,
            (scene.height / 2 - 8) / photo.height
        )
        scene.layers[i].set_effect('sepia', amount=i / 4)


@drawing_test
def test_greyscale(scene):
    """We can convert an image to grey."""
    coords = grid_coords((2, 2), (scene.width, scene.height))
    for i, pos in enumerate(coords, start=1):
        photo = scene.layers[i].add_sprite('positano', pos=pos)
        photo.scale = min(
            (scene.width / 2 - 8) / photo.width,
            (scene.height / 2 - 8) / photo.height
        )
        scene.layers[i].set_effect('greyscale', amount=i / 4)
