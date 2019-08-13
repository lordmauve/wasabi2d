import math
import numpy as np
import moderngl

from ..color import convert_color
from ..allocators.vertlists import VAO
from ..sprites import Transformable


def line_vao(
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a VAO for rendering lines."""
    return VAO(
        mode=moderngl.LINE_STRIP,
        ctx=ctx,
        prog=shadermgr.get(
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
        ),
        dtype=np.dtype([
            ('in_vert', '2f4'),
            ('in_color', '4f4'),
        ])
    )


class Circle(Transformable):
    """A circle drawn with lines."""

    def __init__(
            self,
            pos=(0, 0),
            radius=100,
            color=(1, 1, 1, 1),
            segments=None):
        super().__init__()
        self.segments = segments or max(4, round(radius * math.pi))
        self.pos = pos
        self._radius = radius

        theta = np.linspace(0, 2 * np.pi, self.segments)
        self.orig_verts = np.vstack([
            radius * np.cos(theta),
            radius * np.sin(theta),
            np.ones(self.segments)
        ]).T.astype('f4')
        self._color = convert_color(color)

    def _indices(self):
        return np.linspace(
            0,
            self.segments - 1,
            self.segments,
            dtype='i4'
        )

    def _migrate(self, vao: VAO):
        """Migrate this object into the given VAO."""
        self.vao = vao
        self.lst = vao.alloc(self.segments, self.segments)
        self.lst.indexbuf[:] = self._indices()
        self._update()

    def _update(self):
        xform = self._scale @ self._rot @ self._xlate

        self.lst.vertbuf['in_vert'] = (self.orig_verts @ xform)[:, :2]
        self.lst.vertbuf['in_color'] = self._color
