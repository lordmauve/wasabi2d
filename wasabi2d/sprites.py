import numpy as np

from .primitives.base import Colorable, Transformable, Bounds


TEXTURED_QUADS_PROGRAM = dict(
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
QUAD = np.array([0, 1, 2, 0, 2, 3], dtype='i4')


class SpriteArray:
    """Vertex array object to hold textured quads."""
    PROGRAM = TEXTURED_QUADS_PROGRAM

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
            QUAD + 4 * i
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

            # TODO: We can send less data with write_chunks()
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
            if s._dirty:
                self.verts[i * 4:i * 4 + 4] = s.verts
                self.uvs[i * 4:i * 4 + 4] = s.uvs
                s._dirty = False
                dirty = True
        assert self.verts.dtype == 'f4', \
            f"Dtype of verts is {self.verts.dtype}"
        if dirty:
            self.vbo.write(self.verts)
            self.uvbo.write(self.uvs)
        self.vao.render(vertices=self.allocated * 6)


class Sprite(Colorable, Transformable):
    def __init__(
            self,
            layer,
            image,
            anchor=None):
        super().__init__()
        self.verts = None
        self.layer = layer
        self.array = None
        self._image = None
        self._vert_color = np.ones((4, 4), dtype='f4')
        self.image = image  # trigger sprite load and migration

    @property
    def image(self):
        """Get the name of the image for this sprite."""
        return self._image

    @image.setter
    def image(self, name):
        """Set the image."""
        if name == self._image:
            return

        self._image = name
        tex, uvs, vs = self.layer.group.atlas.get(name)
        self.uvs = np.copy(uvs)
        self.orig_verts = np.copy(vs)
        xs = self.orig_verts[:, 0]
        ys = self.orig_verts[:, 1]
        self.width = np.fabs(np.min(xs) - np.max(xs))
        self.height = np.fabs(np.min(ys) - np.max(ys))
        # TODO: apply anchor to the verts
        self._dirty = True

        if not self.array:
            # initial migration into an array
            self.layer._migrate_sprite(self, tex)
        elif tex != self.array.tex:
            # migrate to a different vao
            self.array.delete(self)
            self.layer._migrate_sprite(self, tex)

    def delete(self):
        """Delete this sprite."""
        self.layer._dirty.discard(self)
        self.layer.objects.discard(self)
        self.array.delete(self)
        self.layer = None

    def _set_dirty(self):
        self.layer._dirty.add(self)
        self.verts = None

    bounds = Bounds('self.orig_verts[:, :2]')

    def _update(self):
        xform = self._scale @ self._rot @ self._xlate

        self._vert_color[:] = self._color
        self.verts = np.hstack([
            self.orig_verts @ xform,
            self._vert_color,
        ])
        self._dirty = True
