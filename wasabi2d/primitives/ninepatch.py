"""Scalable textured panels with fixed-width borders."""
from numbers import Real
from typing import NamedTuple, Optional, Tuple

import moderngl
import numpy as np

from ..allocators.packed import PackedBuffer
from ..atlas import TextureRegion
from .base import Bounds, Colorable, CoroContext, Transformable
from .sprites import TextureContext


class NinePatch(NamedTuple):
    """Describe the stretchable area of an image.

    ``hcuts`` and ``vcuts`` contain the start and end coordinates of the
    stretchable center, measured in source-image pixels.
    """

    image: str
    hcuts: Tuple[int, int]
    vcuts: Tuple[int, int]


NINE_PATCH_DTYPE = np.dtype([
    ('in_vert', '2f4'),
    ('in_color', '4f2'),
    ('in_uv', '2u2'),
])


def _make_indices() -> np.ndarray:
    """Build triangle indices for the nine cells in a 4 by 4 grid."""
    indices = []
    for row in range(3):
        for col in range(3):
            tl = row * 4 + col
            tr = tl + 1
            bl = tl + 4
            br = bl + 1
            indices.extend((tl, tr, br, tl, br, bl))
    return np.array(indices, dtype='u4')


NINE_PATCH_INDICES = _make_indices()


class NinePatchPrimitive(Colorable, Transformable, CoroContext):
    """A textured rectangle whose corners and edges do not stretch."""

    def __init__(
        self,
        layer,
        patch: NinePatch,
        *,
        width: Optional[float] = None,
        height: Optional[float] = None,
        pos: Tuple[float, float] = (0, 0),
        angle: float = 0,
        scale: float = 1.0,
        color=(1, 1, 1, 1),
    ):
        super().__init__()
        self.layer = layer
        self._patch = None
        self._region: Optional[TextureRegion] = None
        self._array = None
        self._array_id = None
        self._width = self._validate_dimension('width', width)
        self._height = self._validate_dimension('height', height)

        self.patch = patch
        self.pos = pos
        self.angle = angle
        self.scale = scale
        self.color = color

    @staticmethod
    def _validate_dimension(name, value):
        if value is None:
            return None
        if not isinstance(value, Real) or value <= 0:
            raise ValueError(f'{name} must be a positive number')
        return float(value)

    @staticmethod
    def _validate_cuts(name, cuts, extent):
        if len(cuts) != 2:
            raise ValueError(f'{name} must contain exactly two coordinates')
        start, end = cuts
        if not 0 <= start <= end <= extent:
            raise ValueError(
                f'{name} must satisfy 0 <= start <= end <= {extent}'
            )

    @property
    def patch(self) -> NinePatch:
        """The image and source-image cut coordinates used by this object."""
        return self._patch

    @patch.setter
    def patch(self, patch: NinePatch):
        if patch == self._patch:
            return
        if not isinstance(patch, NinePatch):
            raise TypeError('patch must be a NinePatch')

        region = self.layer.group.atlas.get(patch.image)
        self._validate_cuts('hcuts', patch.hcuts, region.width)
        self._validate_cuts('vcuts', patch.vcuts, region.height)

        old_array = self._array
        old_array_id = self._array_id
        array = self._get_array(region.tex)
        if old_array is not array:
            if old_array is not None:
                old_array.remove(old_array_id)
            self._array = array
            self._array_id, _ = array.alloc(16, NINE_PATCH_INDICES)

        self._patch = patch
        self._region = region
        if self._width is None:
            self._width = float(region.width)
        if self._height is None:
            self._height = float(region.height)
        self._set_dirty()

    @property
    def width(self) -> float:
        """The unscaled width of the rendered panel."""
        return self._width

    @width.setter
    def width(self, value):
        value = self._validate_dimension('width', value)
        if value is None:
            raise ValueError('width cannot be None after creation')
        if value != self._width:
            self._width = value
            self._set_dirty()

    @property
    def height(self) -> float:
        """The unscaled height of the rendered panel."""
        return self._height

    @height.setter
    def height(self, value):
        value = self._validate_dimension('height', value)
        if value is None:
            raise ValueError('height cannot be None after creation')
        if value != self._height:
            self._height = value
            self._set_dirty()

    def _get_array(self, tex):
        key = ('ninepatch', id(tex))
        array = self.layer.arrays.get(key)
        if array is None:
            program = self.layer.group.shadermgr.load('texquads')
            array = PackedBuffer(
                moderngl.TRIANGLES,
                self.layer.ctx,
                program,
                dtype=NINE_PATCH_DTYPE,
                draw_context=TextureContext(tex, program),
            )
            self.layer.arrays[key] = array
        return array

    @staticmethod
    def _axis_positions(size, start_cut, end_cut, source_size):
        """Return four centered coordinates, shrinking borders if needed."""
        start_border = float(start_cut)
        end_border = float(source_size - end_cut)
        border_size = start_border + end_border
        if size < border_size and border_size:
            factor = size / border_size
            start_border *= factor
            end_border *= factor
        half = size * 0.5
        return (-half, -half + start_border, half - end_border, half)

    def _local_vertices(self):
        xs = self._axis_positions(
            self.width, *self.patch.hcuts, self._region.width
        )
        ys = self._axis_positions(
            self.height, *self.patch.vcuts, self._region.height
        )
        return np.array(
            [(x, y, 1.0) for y in ys for x in xs],
            dtype='f4',
        )

    def _texture_coordinates(self):
        xcuts = (0, *self.patch.hcuts, self._region.width)
        ycuts = (0, *self.patch.vcuts, self._region.height)
        tl, tr, br, bl = self._region.texcoords.astype('f4')
        coords = []
        for y in ycuts:
            fy = y / self._region.height
            left = tl * (1 - fy) + bl * fy
            right = tr * (1 - fy) + br * fy
            for x in xcuts:
                fx = x / self._region.width
                coords.append(left * (1 - fx) + right * fx)
        return np.rint(coords).astype('u2')

    def _set_dirty(self):
        if self.layer is not None:
            self.layer._dirty.add(self)

    bounds = Bounds('self._local_vertices() @ self._xform()[:, :2]')

    def _update(self):
        verts = self._array.get_verts(self._array_id)
        np.matmul(
            self._local_vertices(),
            self._xform()[:, :2],
            out=verts['in_vert'],
        )
        verts['in_color'][:] = self._color
        verts['in_uv'][:] = self._texture_coordinates()

    def delete(self):
        """Delete this primitive and release its buffer allocation."""
        if self.layer is None:
            return
        self.layer._dirty.discard(self)
        self.layer.objects.discard(self)
        self._array.remove(self._array_id)
        self.layer = None
        self._array = self._array_id = None

    def is_alive(self) -> bool:
        """Return true until the primitive has been deleted."""
        return self.layer is not None
