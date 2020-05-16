"""Test harness for testing drawing capabilities."""
import os
import warnings
from typing import Tuple, Iterable
from itertools import product
from pathlib import Path

import numpy as np
import pygame.image
import pygame.surfarray

from wasabi2d.scene import HeadlessScene, capture_screen

ROOT = Path(__file__).parent


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

    failname = ROOT / 'failed-image' / f'{name}.png'

    if np.allclose(comp_surf, exp_surf, atol=2):
        if failname.exists():
            failname.unlink()
        return

    failname.parent.mkdir(exist_ok=True)

    out = pygame.Surface(
        (scene.width * 2 + 1, scene.height),
        depth=32,
    )
    out.blit(computed, (0, 0))
    out.blit(expected, (scene.width + 1, 0))
    WHITE = (255, 255, 255)
    FONTHEIGHT = 40
    pygame.draw.line(
        out,
        WHITE,
        (scene.width, 0),
        (scene.width, scene.height),
    )
    font = pygame.font.SysFont(pygame.font.get_default_font(), FONTHEIGHT)
    y = scene.height - FONTHEIGHT
    out.blit(font.render("Computed", True, WHITE), (10, y))
    lbl = font.render("Expected", True, WHITE)
    out.blit(lbl, (scene.width * 2 - 9 - lbl.get_width(), y))
    pygame.image.save(out, str(failname))

    raise AssertionError(
        "Images differ; saved comparison images to {}".format(failname)
    )


def drawing_test(testfunc):
    """Decorator to run a test function as a drawing test.

    The function will receive a new HeadlessScene object to populate. After the
    function returns it is is automatically asserted that the scene renders
    exactly as per the reference image, using assert_screen_match() as above.

    """
    testname = testfunc.__name__

    def wrapper():
        try:
            scn = HeadlessScene(rootdir=ROOT)
            testfunc(scn)
            scn.draw(0, 0, True)
            assert_screen_match(scn, testname)
        except AssertionError:
            raise
        except Exception:
            failname = ROOT / 'failed-image' / f'{testname}.png'
            if failname.exists():
                failname.unlink()
            raise
        finally:
            scn.release()

    # Can't use functools.wraps() because it copies spec and confuses
    # pytest.
    wrapper.__name__ = testfunc.__name__
    wrapper.__doc__ = testfunc.__doc__
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
