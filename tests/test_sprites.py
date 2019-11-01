"""Tests of sprite drawing."""
import os
import warnings
import tempfile
from typing import Tuple, Iterable
from functools import wraps
from itertools import product
from pathlib import Path
import colorsys

from pytest import fixture
import numpy as np
import pygame.image
import pygame.surfarray

from wasabi2d.scene import HeadlessScene, capture_screen

ROOT = Path(__file__).parent


@fixture
def scene():
    """Return a new headless scene."""
    return HeadlessScene(rootdir=ROOT)


def assert_screen_match(scene, name):
    """Check that the image on the screen matches the reference image.

    If the reference image is missing, raise an exception, unless the
    environment variable $W2D_SAVE_REF is given; if given, save current output
    as new reference images. These will need to be checked and committed.

    """
    ref_image = ROOT / 'expected-image' / f'{name}.png'

    computed = capture_screen(scene.ctx.screen)
    if not ref_image.exists():
        if os.environ.get('W2D_SAVE_REF'):
            warnings.warn(
                f"No reference image exists for {name}; saving new screenshot",
                UserWarning
            )
            pygame.image.save(computed, str(ref_image))
            return
        else:
            raise AssertionError(
                f"No reference image exists for {name}; set $W2D_SAVE_REF "
                "to create."
            )
    else:
        expected = pygame.image.load(str(ref_image))

    comp_surf = pygame.surfarray.array3d(computed)
    exp_surf = pygame.surfarray.array3d(expected)

    if np.allclose(comp_surf, exp_surf, atol=2):
        return

    tmpdir = Path(tempfile.mkdtemp())
    pygame.image.save(computed, str(tmpdir / 'computed.png'))
    pygame.image.save(expected, str(tmpdir / 'expected.png'))

    raise AssertionError(
        "Images differ; saved comparison images to {}".format(tmpdir)
    )


def drawing_test(testfunc):
    """Decorator to run a test function as a drawing test.

    The function will receive a new HeadlessScene object to populate. After the
    function returns it is is automatically asserted that the scene renders
    exactly as per the reference image, using assert_screen_match() as above.

    """
    @wraps(testfunc)
    def wrapper(scene):
        testfunc(scene)
        scene.draw(0, 0)
        assert_screen_match(scene, testfunc.__name__)
    return wrapper


def grid_coords(
    cells: Tuple[int, int],
    page: Tuple[int, int] = (800, 600)
) -> Iterable[Tuple[float, float]]:
    """Return a sequence of center coordinates for subdividing page into cells.

    `cells` gives the number of cells wide x high.

    """
    cells = np.array(cells, dtype=np.int32)
    page = np.array(page, dtype=np.float32)
    cellsize = page / cells
    left, top = cellsize / 2.0
    right, bottom = page - cellsize / 2.0
    xs = np.linspace(left, right, cells[0])
    ys = np.linspace(top, bottom, cells[1])
    return ((x, y) for y, x, in product(ys, xs))


@drawing_test
def test_draw_sprite(scene):
    """We can draw a sprite to the scene."""
    scene.layers[0].add_sprite('ship', pos=(400, 300))


@drawing_test
def test_draw_stars(scene):
    """We can draw stars ."""
    for i, pos in enumerate(grid_coords((4, 3))):
        color = colorsys.hsv_to_rgb(i / 12, 1, 1)
        scene.layers[0].add_star(
            inner_radius=2 * i + 2,
            outer_radius=3 * i + 10,
            points=2 * i + 3,
            pos=pos,
            color=color
        )
