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
    ('xform', '(2,3)f4'),
    ('dims', '2f4'),
    ('in_color', '4f4'),
    ('uvmap', '(2,3)f4'),
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
        super().__init__()
        self.layer = layer
        self.patch = patch
        self._data['dims'] = (
            width or self._region.width,
            height or self._region.height,
        )
        self.pos = pos
        self.angle = angle
        self.color = color

    def _init_data(self):
        self._data['in_color'] = 1.0
        self._color = self._data['in_color']
        self._data['xform'] = (
            (1.0, 0.0),
            (0.0, 1.0),
            (0.0, 0.0)
        )

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

        self._array_id, (newdata,) = self._array.alloc(1, [0])
        if self._data is None:
            self._data = newdata
            self._init_data()
        else:
            # Copy existing data into new storage
            newdata[:] = self._data
            self._data = newdata

        # TODO: move this operation into TextureRegion
        tl, tr, br, bl = self._region.texcoords.astype(np.float32)
        self._data['uvmap'] = [
            tr - tl,
            bl - tl,
            tl
        ]
        self._data['cuts'] = patch.hcuts + patch.vcuts

        self._dirty = True

    def _get_array(self, tex):
        k = ('9patch', id(tex))
        array = self.layer.arrays.get(k)
        if not array:
            prog = self.layer.group.shadermgr.load(
                'ninepatch',
                'ninepatch',
                'texquads'
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
