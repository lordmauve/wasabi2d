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
    scene.background = '#cccccc'
    colors = ['red', 'blue', 'green', 'yellow']
    for i, pos in enumerate(grid_coords((4, 3))):
        filled = not i % 2
        c = scene.layers[0].add_circle(
            radius=3 * i + 10,
            pos=pos,
            fill=filled,
            color=colors[i % len(colors)],
            stroke_width=i
        )
        c.color = (*c.color[:3], (i + 2) / 13)


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
        )
        r.angle = i * 0.1


@drawing_test
def test_draw_rect_origin(scene):
    """We can draw a rectangle centred at the origin."""
    scene.background = '#223366'
    scene.camera.pos = 0, 0
    scene.layers[0].add_rect(
        100, 100,
        pos=(0, 0),
        fill=False,
        stroke_width=4
    )


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


@drawing_test
def test_aa(scene):
    """Shapes are correctly composited onto each other."""
    w = scene.width
    h = scene.height
    mid = (w / 2, h / 2)
    scene.background = 'cyan'
    r = scene.layers[0].add_rect(200, 20, pos=mid, color='red')
    r.angle = 0.2
    scene.layers[0].add_star(
        inner_radius=50,
        outer_radius=100,
        points=7,
        pos=mid,
        color='yellow'
    )


@drawing_test
def test_aa_blend(scene):
    """The alpha curve is as expected."""
    scene.background = '#888888'

    for i, pos in enumerate(grid_coords((40, 30))):
        y, x = divmod(i, 40)
        scene.layers[1].add_circle(
            radius=8,
            pos=pos,
            color=(y / 60, 0, y / 60, x / 80),
        )


@drawing_test
def test_coincident_points(scene):
    """With coincident points we still get a line segment."""
    center = scene.width // 2, scene.height // 2

    angles = np.linspace(0, np.pi * 2, 20)
    points = np.array([
        np.cos(angles),
        np.sin(angles),
    ]).T * 200 + center

    scene.layers[0].add_polygon(
        points,
        fill=False,
        color=(0.9, 0.9, 1.2),
        stroke_width=4
    )
