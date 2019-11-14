"""Regression tests for shader effects.

For all tests we compare rendering to a reference image generated with a
previous version of the software. We expect near pixel-perfect output, allowing
for variations in calculation accuracy.

"""
from wasabi2d import chain
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


@drawing_test
def test_posterize(scene):
    """We can posterize an image."""
    coords = grid_coords((2, 2), (scene.width, scene.height))
    for i, pos in enumerate(coords, start=1):
        photo = scene.layers[i].add_sprite('positano', pos=pos)
        photo.scale = min(
            (scene.width / 2 - 8) / photo.width,
            (scene.height / 2 - 8) / photo.height
        )
        scene.layers[i].set_effect('posterize', levels=3 + i, gamma=0.5 * i)


@drawing_test
def test_mask(scene):
    """We can mask one layer using another layer."""
    center = (scene.width / 2, scene.height / 2)
    scene.layers[0].add_sprite('positano', pos=center)
    scene.layers[1].add_circle(radius=200, pos=center)
    scene.chain = [
        chain.Mask(
            mask=1,
            paint=0,
        )
    ]


@drawing_test
def test_mask_outside(scene):
    """We can mask one layer to *outside* another layer."""
    center = (scene.width / 2, scene.height / 2)
    scene.layers[0].add_sprite('positano', pos=center)
    scene.layers[1].add_circle(radius=200, pos=center)
    scene.chain = [
        chain.Mask(
            mask=1,
            paint=0,
            function='outside',
        )
    ]


@drawing_test
def test_mask_luminance(scene):
    """We can mask one layer using the luminance of the other layer."""
    center = (scene.width / 2, scene.height / 2)
    scene.background = 'white'
    # Flip these around, as the photo has luminance variations
    scene.layers[1].add_sprite('positano', pos=center)
    scene.layers[0].add_circle(
        radius=200,
        pos=center,
        color='magenta'
    )
    scene.chain = [
        chain.Mask(
            mask=1,
            paint=0,
            function='luminance',
        ).wrap_effect('dropshadow', offset=(10, 10))
    ]
