"""Nine patch primitive."""
from dataclasses import dataclass
from typing import Tuple, Dict, Set, Optional, List, TypeVar, Union
from typing import NamedTuple

import moderngl
import numpy as np

from ..atlas import TextureRegion
from .base import Transformable, Colorable
from ..allocators.packed import PackedBuffer
from .sprites import TextureContext


class NinePatch(NamedTuple):
    """The definition of a nine patch.

    We keep this separate from the primitive because it's likely to be
    re-used across many instances of the primitive, saved/loaded etc.
    """
    image: str
    hcuts: Tuple[int, int]
    vcuts: Tuple[int, int]


NINE_PATCH_DTYPE = np.dtype([
    ('xform', '(3,2)f4'),
    ('dims', '2f4'),
    ('color', '4f4'),
    ('uvmap', '(3,2)f4'),
    ('cuts', '4u2'),
])


class NinePatchPrimitive(Colorable, Transformable):
    patch: NinePatch
    width: float
    height: float

    _data = None
    _array = None
    _region: TextureRegion
    _patch: NinePatch = None

    def __init__(
        self,
        layer,
        patch: NinePatch,
        *,
        width: Optional[float] = None,
        height: Optional[float] = None,
        pos: Tuple[float, float] = (0, 0),
        angle: float = 0,
        color: Tuple[float, float, float, float] = (1, 1, 1, 1),
    ):
        self._color = np.ones(4, dtype=np.float32)
        self._dims = (width, height)
        super().__init__()
        self.layer = layer
        self.patch = patch
        self.pos = pos
        self.angle = angle
        self.color = color

    def _copy_data(self, data):
        """Copy data into the contiguous buffer."""
        data['xform'] = self._xform()[:, :2]
        data['color'] = self._color
        data['dims'] = self._dims

    @property
    def patch(self) -> NinePatch:
        """Get the patch details for this nine-patch."""
        return self._patch

    @patch.setter
    def patch(self, patch: NinePatch):
        """Set the patch."""
        if patch == self._patch:
            return

        self._patch = patch

        self._region = self.layer.group.atlas.get(patch.image)
        tex = self._region.tex
        if not self._array:
            # migrate into a new array
            self._array = self._get_array(tex)
        elif tex is not self._array.draw_context.tex:
            # migrate out of this buffer
            self._array.remove(self._array_id)
            self._array = self._get_array(tex)

        indices = np.array([0], dtype=np.uint32)
        self._array_id, (data,) = self._array.alloc(1, indices)
        # if self._data is None:
        #     self._data = newdata
        #     self._init_data()
        # else:
        #     # Copy existing data into new storage
        #     newdata[:] = self._data
        #     self._data = newdata

        dw, dh = self._dims
        self._dims = (
            dw if dw is not None else self._region.width,
            dh if dh is not None else self._region.height,
        )

        # TODO: move this operation into TextureRegion
        tl, tr, br, bl = self._region.texcoords.astype(np.float32)
        data['uvmap'] = [
            tr - tl,
            bl - tl,
            tl
        ]
        data['cuts'] = patch.hcuts + patch.vcuts
        self._copy_data(data)

    def _get_array(self, tex):
        k = ('9patch', id(tex))
        array = self.layer.arrays.get(k)
        if not array:
            prog = self.layer.group.shadermgr.load(
                'ninepatch',
                'ninepatch',
                'ninepatch', #'texquads'
            )
            array = PackedBuffer(
                moderngl.POINTS,
                self.layer.ctx,
                prog,
                dtype=NINE_PATCH_DTYPE,
                draw_context=TextureContext(tex, prog),
            )
            self.layer.arrays[k] = array
        return array

    def _set_dirty(self):
        if self.layer:
            self.layer._dirty.add(self)

    def _update(self):
        data, = self._array.get_verts(self._array_id)
        self._copy_data(data)
