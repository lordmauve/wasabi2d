import math
from functools import partial

import numpy as np
import moderngl

from ..color import convert_color
from ..allocators.vertlists import VAO
from .polygons import AbstractShape
from ..rect import ZRect
from ..descriptors import CallbackProp
from ..effects.base import PostprocessPass
from ..shaders import bind_framebuffer, blend_func


class PolyVAO(VAO):
    """VAO object that renders with multisampling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.composite_prog = PostprocessPass(
            self.ctx,
            'postprocess/multisample_blend'
        )

    def render(self, camera):
        samples = min(self.ctx.max_samples, 4)
        with camera.temporary_fb(samples=samples) as fb:
            with bind_framebuffer(self.ctx, fb, clear=True):
                super().render(camera)
            self.composite_prog.render(image=fb, samples=samples)


def color_vao(
        mode: int,
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a BAO for rendering plain colored objects."""
    return PolyVAO(
        mode=mode,
        ctx=ctx,
        prog=shadermgr.load('primitives/flat_color'),
        dtype=np.dtype([
            ('in_vert', '2f4'),
            ('in_color', '4f4'),
        ])
    )


def line_vao(
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a VAO for rendering lines."""
    return PolyVAO(
        mode=moderngl.LINE_STRIP_ADJACENCY,
        ctx=ctx,
        prog=shadermgr.load(
            'primitives/wide_line',
            'primitives/wide_line',
            'primitives/flat_color',
        ),
        dtype=np.dtype([
            ('in_vert', '2f4'),
            ('in_color', '4f4'),
            ('in_linewidth', 'f4'),
        ])
    )


#: Construct a VAO for rendering the fill of shapes
shape_vao = partial(color_vao, moderngl.TRIANGLES)


class Circle(AbstractShape):
    """A circle drawn with lines."""

    __slots__ = (
        'layer', 'segments',
        '_radius',
        'orig_verts',
    )

    def __init__(
            self,
            layer,
            pos=(0, 0),
            radius=100,
            color=(1, 1, 1, 1),
            stroke_width=1.0,
            segments=None):
        super().__init__()
        self.layer = layer
        self.segments = segments or max(4, round(math.pi * radius))
        self.pos = pos
        self._stroke_width = stroke_width

        # Generate verts now
        theta = np.linspace(0, 2 * np.pi, self.segments).reshape((-1, 1))
        self.base_verts = np.hstack([
            np.cos(theta),
            np.sin(theta),
        ]).astype('f4')

        # There's a duplicate vertex so move the first vertex to the center
        self.base_verts[0][:2] = 0

        # Placeholder for scaled verts
        self.orig_verts = np.ones((self.segments, 3), dtype='f4')

        # Assigning radius generates self.orig_verts
        self.radius = radius

        self._color = convert_color(color)
        self._set_dirty()

    def _on_set_radius(self):
        np.multiply(
            self.base_verts,
            self._radius,
            self.orig_verts[:, :2]
        )
        self._set_dirty()

    radius = CallbackProp(_on_set_radius)

    def _stroke_indices(self):
        """Indexes for drawing the stroke as a LINE_STRIP."""
        n = self.segments
        return np.array(
            [n - 1, *range(1, n), 1, 2],
            dtype='i4'
        )

    def _fill_indices(self):
        """Indexes for drawing the fill as TRIANGLES."""
        idxs = np.array([
            (0, i, i + 1)
            for i in range(1, self.segments)
        ], dtype='i4')
        idxs[-1][2] = 1
        return idxs.reshape((-1))

    @property
    def bounds(self):
        x, y = self.pos
        r = self.radius * self.scale
        return ZRect(
            (x - r, y - r),
            (r * 2, r * 2),
        )
