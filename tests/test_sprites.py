"""Regression tests for sprite drawing."""
import random
from unittest.mock import patch

import numpy as np
from pygame import Surface
import pygame.draw

from wasabi2d.loaders import images

from drawing_utils import drawing_test


@drawing_test
def test_draw_sprite(scene):
    """We can draw a sprite to the scene."""
    scene.layers[0].add_sprite('ship', pos=(400, 300))


@drawing_test
def test_draw_many_sprites(scene):
    """Test that we can draw hundreds of large sprites.

    We want to test that we grow the available texture space when necessary, so
    we generate and pre-cache new sprites.

    """
    scene.layers[1].add_sprite('ship', pos=(400, 300))
    rng = random.Random(0)
    with patch.dict(images.__dict__, _cache={}):
        for i in range(100):
            s = Surface((64, 64), flags=pygame.SRCALPHA, depth=32)
            segments = rng.randint(6, 9)
            theta = np.linspace(0, 2 * np.pi, segments).reshape((-1, 1))
            verts = np.hstack([
                np.cos(theta),
                np.sin(theta),
            ]).astype('f4')
            radii = np.array([rng.uniform(10, 30) for _ in verts])
            verts *= radii[:, np.newaxis]
            verts += (32, 32)
            color = np.array((rng.randint(128, 200),) * 3, dtype=np.uint8)
            pygame.draw.polygon(
                s,
                points=verts,
                color=color
            )
            pygame.draw.polygon(
                s,
                points=verts,
                color=color // 2,
                width=2,
            )
            k = f'rock{i}'
            images._cache[k, (), ()] = s
            scene.layers[0].add_sprite(
                k,
                pos=(
                    rng.uniform(0, 800),
                    rng.uniform(0, 600),
                )
            )
    assert len(scene.layers.atlas.packer.texs) > 1


@drawing_test
def test_draw_labels(scene):
    """We can draw text labels."""
    scene.background = '#ccccff'
    scene.layers[0].add_label(
        "Left\naligned.",
        pos=(10, 50),
        color='navy'
    )
    scene.layers[0].add_label(
        "or right",
        font="eunomia_regular",
        fontsize=60,
        pos=(790, 200),
        align="right",
        color=(0.5, 0, 0),
    )
    scene.layers[0].add_label(
        "Center über alles",
        fontsize=40,
        pos=(400, 500),
        align="center",
        color='black',
    )
