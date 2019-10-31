"""Tests of sprite drawing."""
import os
import warnings
import tempfile
from pathlib import Path
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
    """Check that the image on the screen matches the reference image."""
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


def test_draw_sprite(scene):
    """We can draw a sprite to the scene."""
    scene.layers[0].add_sprite('ship', pos=(400, 300))
    scene.draw(0, 0)
    assert_screen_match(scene, 'test_draw_sprite')
