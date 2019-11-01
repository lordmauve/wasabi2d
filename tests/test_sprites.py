"""Tests of sprite drawing."""
import colorsys
from drawing_utils import drawing_test, grid_coords


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
