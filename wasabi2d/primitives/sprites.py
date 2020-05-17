from dataclasses import dataclass

import numpy as np
import moderngl

from ..descriptors import CallbackProp
from .base import Colorable, Transformable, Bounds
from ..allocators.packed import PackedBuffer


QUAD = np.array([0, 1, 2, 0, 2, 3], dtype='u4')


@dataclass
class TextureContext:
    tex: moderngl.Texture
    prog: moderngl.Program

    def __enter__(self):
        """Bind the given texture to the given program during the context."""
        self.prog['tex'].value = 0
        self.tex.use(0)

    def __exit__(self, *_):
        pass


class Sprite(Colorable, Transformable):
    """A sprite is a quad with an image texture."""

    def __init__(
            self,
            layer,
            image,
            anchor_x='center',
            anchor_y='center'):
        super().__init__()
        self.verts = None
        self.layer = layer
        self._image = None
        self._anchor_x = anchor_x
        self._anchor_y = anchor_y
        self._vert_color = np.ones((4, 4), dtype='f4')

        self._array = None
        self._array_id = None

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

        if not self._array:
            # migrate into a new array
            self._array = self._get_array(tex)
            self._array_id, _ = self._array.alloc(4, QUAD)
        elif tex is not self._array.draw_context.tex:
            # migrate out of this buffer
            self._array.remove(self._array_id)
            self._array = self._get_array(tex)
            self._array_id, _ = self._array.alloc(4, QUAD)

    def _get_array(self, tex):
        k = ('sprite', id(tex))
        array = self.layer.arrays.get(k)
        if not array:
            prog = self.layer.group.shadermgr.load('texquads')
            array = PackedBuffer(
                moderngl.TRIANGLES,
                self.layer.ctx,
                prog,
                dtype=np.dtype([
                    ('in_vert', '2f4'),
                    ('in_color', '4f2'),
                    ('in_uv', '2u2'),
                ]),
                draw_context=TextureContext(tex, prog),
            )
            self.layer.arrays[k] = array
        return array

    def _reset_verts(self):
        self.orig_verts = None
        self._set_dirty()

    anchor_x = CallbackProp(_reset_verts)
    anchor_y = CallbackProp(_reset_verts)

    def delete(self):
        """Delete this sprite."""
        self.layer._dirty.discard(self)
        self.layer.objects.discard(self)
        self._array.remove(self._array_id)
        self.layer = None
        self._array = self._array_id = None

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

        verts = self._array.get_verts(self._array_id)
        verts['in_color'][:] = self._color
        verts['in_uv'][:] = self.texregion.texcoords

        np.matmul(
            self.orig_verts,
            xform[:, :2],
            out=verts['in_vert']
        )
