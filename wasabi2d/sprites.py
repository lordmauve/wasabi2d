from typing import Any, Optional
from dataclasses import dataclass, field

import numpy as np
from pyrr import Matrix44, Vector3, vector3, matrix33


Z = vector3.create_unit_length_z()



textured_quads_program = dict(
    vertex_shader='''
        #version 330

        uniform mat4 proj;

        in vec3 in_vert;
        in vec4 in_color;
        in vec2 in_uv;
        out vec2 uv;
        out vec4 color;

        void main() {
            gl_Position = proj * vec4(in_vert.xy, 0.0, 1.0);
            uv = in_uv;
            color = in_color;
        }
    ''',
    fragment_shader='''
        #version 330

        out vec4 f_color;
        in vec2 uv;
        in vec4 color;
        uniform sampler2D tex;

        void main() {
            f_color = color * texture(tex, uv);
        }
    ''',
)


class SpriteArray:
    """Vertex array object to hold textured quads."""
    QUAD = np.array([0, 1, 2, 0, 2, 3], dtype='i4')
    PROGRAM = textured_quads_program

    def __init__(self, ctx, prog, tex, sprites):
        self.tex = tex
        self.ctx = ctx
        self.prog = prog
        self.sprites = list(sprites)
        self._allocate()

    def _allocate(self):
        self.allocated = len(self.sprites)

        # Allocate extra slots in the arrays for faster additions
        extra = max(32 - self.allocated, self.allocated // 2)

        for i, s in enumerate(self.sprites):
            s.array = self
            s.offset = i
            if s.verts is None:
                s._update()

        self.indexes = np.vstack([
            self.QUAD + 4 * i
            for i in range(self.allocated + extra)
        ])
        self.uvs = np.vstack(
            [s.uvs for s in self.sprites]
            + [np.zeros((4 * extra, 2), dtype='f4')]
        )
        self.verts = np.vstack(
            [s.verts for s in self.sprites]
            + [np.zeros((4 * extra, 7), dtype='f4')]
        )

        self.vbo = self.ctx.buffer(self.verts, dynamic=True)
        self.uvbo = self.ctx.buffer(self.uvs)
        self.ibuf = self.ctx.buffer(self.indexes)
        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo, '3f 4f', 'in_vert', 'in_color'),
                (self.uvbo, '2f', 'in_uv'),
            ],
            self.ibuf
        )

    def add(self, s):
        """Add a sprite to the array.

        If there's unallocated space in the VBO we append the sprite.

        Otherwise we allocate new VBOs.
        """
        s.array = self
        if not s.verts:
            s._update()
        size = len(self.verts) // 4
        if self.allocated < size:
            i = self.allocated
            self.allocated += 1
            self.verts[i * 4:i * 4 + 4] = s.verts
            self.uvs[i * 4:i * 4 + 4] = s.uvs
            self.sprites.append(s)
            s.offset = i

            #TODO: We can send less data with write_chunks()
            self.vbo.write(self.verts)
            self.uvbo.write(self.uvs)
        else:
            self.sprites.append(s)
            self._allocate()

    def delete(self, s):
        """Remove a sprite from the array.

        To do this without resizing the buffer we move a sprite from the
        end of the array into the gap. This means that draw order changes.

        """
        assert s.array is self
        i = s.offset
        j = self.allocated - 1
        self.allocated -= 1
        if i == j:
            self.sprites.pop()
        else:
            moved = self.sprites[i] = self.sprites[j]
            self.sprites.pop()
            moved.offset = i
            self.verts[i * 4:i * 4 + 4] = self.verts[j * 4:j * 4 + 4]
            self.uvs[i * 4:i * 4 + 4] = self.uvs[j * 4:j * 4 + 4]
            # TODO: write only once per frame no matter how many adds/deletes
            self.vbo.write(self.verts)
            self.uvbo.write(self.uvs)
        s.array = None

    def render(self):
        """Render all sprites in the array."""
        self.prog['tex'].value = 0
        self.tex.use(0)
        dirty = False
        for i, s in enumerate(self.sprites):
            if s.verts is None:
                s._update()
                self.verts[i * 4:i * 4 + 4] = s.verts
                dirty = True
        assert self.verts.dtype == 'f4', \
            f"Dtype of verts is {self.verts.dtype}"
        if dirty:
            self.vbo.write(self.verts)
        self.vao.render(vertices=self.allocated * 6)


@dataclass
class Sprite:
    image: str
    _angle: float

    uvs: np.ndarray
    orig_verts: np.ndarray
    verts: Optional[np.ndarray] = None

    _scale: np.ndarray = field(
        default_factory=lambda: np.identity(3, dtype='f4')
    )
    _rot: np.ndarray = field(
        default_factory=lambda: np.identity(3, dtype='f4')
    )
    _xlate: np.ndarray = field(
        default_factory=lambda: np.identity(3, dtype='f4')
    )
    _color: np.ndarray = field(
        default_factory=lambda: np.ones((4, 4), dtype='f4')
    )

    array: Any = None
    offset: int = 0

    def delete(self):
        self.array.delete(self)

    @property
    def color(self):
        return tuple(self.color[0])

    @color.setter
    def color(self, v):
        self._color[:] = v
        self.verts = None

    @property
    def pos(self):
        return self._xlate[2][:2]

    @pos.setter
    def pos(self, v):
        assert len(v) == 2
        self._xlate[2][:2] = v
        self.verts = None

    @property
    def scale(self):
        p = np.product(np.diagonal(self._scale))
        return np.copysign(np.sqrt(abs(p)), p)

    @scale.setter
    def scale(self, v):
        self._scale[0, 0] = self._scale[1, 1] = v
        self.verts = None

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, theta):
        assert isinstance(theta, (int, float))
        self._rot = matrix33.create_from_axis_rotation(Z, theta, dtype='f4')
        self._angle = theta
        self.verts = None

    def _update(self):
        xform = self._scale @ self._rot @ self._xlate

        self.verts = np.hstack([
            self.orig_verts @ xform,
            self._color
        ])
