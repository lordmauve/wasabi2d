import math
import numpy as np
import moderngl

from ..color import convert_color
from ..allocators.vertlists import VAO
from .polygons import AbstractShape


#: Shader for a plain color fill
PLAIN_COLOR = dict(
    vertex_shader='''
        #version 330

        uniform mat4 proj;

        in vec2 in_vert;
        in vec4 in_color;
        out vec4 color;

        void main() {
            gl_Position = proj * vec4(in_vert, 0.0, 1.0);
            color = in_color;
        }
    ''',
    fragment_shader='''
        #version 330

        out vec4 f_color;
        in vec4 color;

        void main() {
            f_color = color;
        }
    ''',
)


def color_vao(
        mode: int,
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a BAO for rendering plain colored objects."""
    return VAO(
        mode=mode,
        ctx=ctx,
        prog=shadermgr.get(**PLAIN_COLOR),
        dtype=np.dtype([
            ('in_vert', '2f4'),
            ('in_color', '4f4'),
        ])
    )


def line_vao(
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a VAO for rendering lines."""
    return color_vao(
        mode=moderngl.LINE_STRIP,
        ctx=ctx,
        shadermgr=shadermgr,
    )


def shape_vao(
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a VAO for rendering shapes."""
    return color_vao(
        mode=moderngl.TRIANGLES,
        ctx=ctx,
        shadermgr=shadermgr,
    )


class Circle(AbstractShape):
    """A circle drawn with lines."""

    def __init__(
            self,
            layer,
            pos=(0, 0),
            radius=100,
            color=(1, 1, 1, 1),
            segments=None):
        super().__init__()
        self.layer = layer
        self.segments = segments or max(4, round(radius * math.pi))
        self.pos = pos
        self._radius = radius

        theta = np.linspace(0, 2 * np.pi, self.segments)
        self.orig_verts = np.vstack([
            radius * np.cos(theta),
            radius * np.sin(theta),
            np.ones(self.segments)
        ]).T.astype('f4')

        # There's a duplicate vertex so move the first vertex to the center
        self.orig_verts[0][:2] = 0

        self._color = convert_color(color)
        self._set_dirty()

    def _stroke_indices(self):
        """Indexes for drawing the stroke as a LINE_STRIP."""
        idxs = np.linspace(
            0,
            self.segments - 1,
            self.segments,
            dtype='i4'
        )
        idxs[0] = self.segments - 1
        return idxs

    def _fill_indices(self):
        """Indexes for drawing the fill as TRIANGLES."""
        idxs = np.array([
            (0, i, i + 1)
            for i in range(1, self.segments)
        ], dtype='i4')
        idxs[-1][2] = 1
        return idxs.reshape((-1))
