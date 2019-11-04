"""Regression tests for drawing polygonal shapes.

For all tests we compare rendering to a reference image generated with a
previous version of the software. We expect near pixel-perfect output, allowing
for variations in calculation accuracy.

"""
import random
import colorsys

import numpy as np

from drawing_utils import drawing_test, grid_coords


@drawing_test
def test_draw_circles(scene):
    """We can draw circles."""
    colors = ['red', 'blue', 'green', 'yellow']
    for i, pos in enumerate(grid_coords((4, 3))):
        filled = bool(i % 2)
        c = scene.layers[0].add_circle(
            radius=3 * i + 10,
            pos=pos,
            fill=filled,
            color=colors[i % len(colors)],
            stroke_width=i
        )
        c.color = (*c.color[:3], (i + 1) / 12)


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
def test_draw_rects(scene):
    """We can draw rectangles."""
    colors = ['magenta', 'cyan', 'orange', 'white']
    for i, pos in enumerate(grid_coords((4, 3))):
        filled = bool(i % 2)
        w = 60 / (i + 1)
        h = 120 / (12 - i)

        r = scene.layers[0].add_rect(
            w, h,
            pos=pos,
            fill=filled,
            color=colors[i % len(colors)],
            stroke_width=i
        )
        r.angle = i * 0.1


@drawing_test
def test_draw_polygons(scene):
    """We can draw rectangles."""
    scene.background = 'white'
    w = scene.width
    mid = scene.height / 2
    rng = random.Random(0)

    octaves = 6
    segments = 60
    for layer in range(6):
        h = (6 - layer) * scene.height / 24 + 20

        wavelength = np.array([rng.uniform(0.2, 1) for _ in range(octaves)])
        phase = np.array([rng.uniform(0, np.pi) for _ in range(octaves)])
        mag = np.array([rng.uniform(4, 10) for _ in range(octaves)])
        xs = np.linspace(0, w, segments)
        ts = np.linspace(4, 12, segments)[..., np.newaxis]

        ys = np.sum(
            mag[np.newaxis, ...] * np.sin(ts / wavelength + phase),
            axis=1
        )

        upper = np.vstack([xs, mid + h + ys])
        lower = np.vstack([xs, mid - h - ys])
        points = np.vstack([upper.T, lower.T[::-1, ...]])

        scene.layers[0].add_polygon(
            points,
            color=(0.2, 0.2, 1.0, 0.2),
        )
