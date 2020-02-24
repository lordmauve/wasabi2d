from contextlib import contextmanager
import numpy as np

from ..descriptors import CallbackProp
from .base import Colorable, Transformable, Bounds
from ..allocators.packed import PackedBuffer


TEXTURED_QUADS_PROGRAM = dict(
    vertex_shader='''
        #version 330

        uniform mat4 proj;

        in vec3 in_vert;
        in vec4 in_color;
        in ivec2 in_uv;
        out vec2 uv;
        out vec4 color;
        uniform sampler2D tex;

        void main() {
            gl_Position = proj * vec4(in_vert.xy, 0.0, 1.0);
            uv = vec2(in_uv) / textureSize(tex, 0);
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
        self.vao = None
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
            + [np.zeros((4 * extra, 2), dtype=np.uint16)]
        )
        self.verts = np.vstack(
            [s.verts for s in self.sprites]
            + [np.zeros((4 * extra, 7), dtype='f4')]
        )

        self.release()
        self.vbo = self.ctx.buffer(self.verts, dynamic=True)
        self.uvbo = self.ctx.buffer(self.uvs)
        self.ibuf = self.ctx.buffer(self.indexes)
        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo, '3f 4f', 'in_vert', 'in_color'),
                (self.uvbo, '2u2', 'in_uv'),
            ],
            self.ibuf
        )
        self._dirty = False

    def add(self, s):
        """Add a sprite to the array.

        If there's unallocated space in the VBO we append the sprite.

        Otherwise we allocate new VBOs.
        """
        s.array = self
        if s.verts is None:
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
            self._dirty = True
        s.array = None

    def render(self, camera):
        """Render all sprites in the array."""
        dirty = self._dirty
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
            self._dirty = False
        self.vao.render(vertices=self.allocated * 6)

    def release(self):
        if self.vao:
            self.vao.release()
            self.vbo.release()
            self.uvbo.release()
            self.ibuf.release()
            self.vao = None

    __del__ = release


def texture_context(tex, prog):
    """Bind the given texture to the given program during the context."""
    prog['tex'].value = 0
    tex.use(0)
    yield


class Sprite(Colorable, Transformable):
    def __init__(
            self,
            layer,
            image,
            anchor_x='center',
            anchor_y='center'):
        super().__init__()
        self.verts = None
        self.layer = layer
        self.array = None
        self._image = None
        self._anchor_x = anchor_x
        self._anchor_y = anchor_y
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
        texregion = self.texregion = self.layer.group.atlas.get(name)

        self.uvs = texregion.texcoords
        self.orig_verts = texregion.get_verts(self._anchor_x, self._anchor_y)
        xs = self.orig_verts[:, 0]
        ys = self.orig_verts[:, 1]
        self.width = np.fabs(np.min(xs) - np.max(xs))
        self.height = np.fabs(np.min(ys) - np.max(ys))

        self._dirty = True

        tex = self.texregion.tex

        if not self.array:
            # initial migration into an array
            self.layer._migrate_sprite(self, tex)
        elif tex is not self.array.tex:
            # migrate to a different vao
            self.array.delete(self)
            self.layer._migrate_sprite(self, tex)

    def _get_array(self, tex):
        k = ('sprite', id(tex))
        array = self.layer.arrays.get(k)
        if not array:
            prog = self.layer.group.shadermgr.get(**TEXTURED_QUADS_PROGRAM)
            array = PackedBuffer(self.ctx, prog, tex, [spr])
            self.layer.arrays[k] = array

        array.add(spr)

    def _reset_verts(self):
        self.orig_verts = None
        self._set_dirty()

    anchor_x = CallbackProp(_reset_verts)
    anchor_y = CallbackProp(_reset_verts)

    def delete(self):
        """Delete this sprite."""
        self.layer._dirty.discard(self)
        self.layer.objects.discard(self)
        array = self.array
        self.array.delete(self)
        if not array.sprites:
            self.layer._delete_sprite_array(array)
        self.layer = None

    def _set_dirty(self):
        if self.layer:
            self.layer._dirty.add(self)
        self.verts = None

    bounds = Bounds('self.orig_verts[:, :2]')

    def _update(self):
        if self.orig_verts is None:
            self.orig_verts = self.texregion.get_verts(
                self._anchor_x,
                self._anchor_y
            )

        xform = self._xform()

        self._vert_color[:] = self._color
        self.verts = np.hstack([
            self.orig_verts @ xform,
            self._vert_color,
        ])
        self._dirty = True
