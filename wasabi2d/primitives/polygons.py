import numpy as np

mapbox_earcut = None

try:
    import mapbox_earcut
except ModuleNotFoundError:
    from ..vendor.earcut import earcut

from ..color import convert_color
from .base import AbstractShape


class Polygon(AbstractShape):
    """An arbitrary polygon."""

    def __init__(
            self,
            layer,
            vertices,
            *,
            pos=(0, 0),
            color=(1, 1, 1, 1),
            stroke_width=1.0):
        self.orig_verts = np.ones((len(vertices), 3), dtype='f4')
        self.orig_verts[:, :2] = vertices

        super().__init__()
        self.layer = layer
        self.pos = pos
        self._stroke_width = stroke_width

        self._color = convert_color(color)
        self._set_dirty()

    @property
    def vertices(self):
        """Get the vertices of the polygon."""
        return self.orig_verts[:, :2].copy()

    @vertices.setter
    def vertices(self, v):
        """Set the vertices of the polygon.

        It is currently not allowed to increase or decrease the number of
        vertices.
        """
        self.orig_verts[:, :2] = v
        self._set_dirty()

    def _stroke_indices(self):
        """Indexes for drawing the stroke as a LINE_STRIP_ADJACENCY."""
        verts = len(self.orig_verts)
        idxs = np.arange(verts, dtype='i4')
        winding = idxs[[-1, *idxs, 0, 1, 2]]
        return winding

    def _fill_indices_mapbox_earcut(self):
        """Indexes for drawing the fill as TRIANGLES.
        
        This version uses the mapbox_earcut library, which is C++, but
        currently doesn't have a Python 3.8 release. See

        https://github.com/skogler/mapbox_earcut_python/issues/2

        """
        verts = self.orig_verts[:, :2]
        rings = np.array([len(verts)], dtype=np.uint32)
        idxs = mapbox_earcut.triangulate_float32(verts, rings)
        return idxs.reshape(-1)

    def _fill_indices_earcut(self):
        """Indexes for drawing the fill as TRIANGLES.
        
        This version uses a pure-Python library, which is vendored into this
        repo.
        """
        verts = self.orig_verts[:, :2].reshape((-1)).astype(np.int64)
        idxs = earcut(verts)
        return np.array(idxs, dtype='i4')

    if mapbox_earcut:
        _fill_indices = _fill_indices_mapbox_earcut
    else:
        _fill_indices = _fill_indices_earcut


class Rect(Polygon):
    """A rectangle."""
    VERTS = np.array([
        (-0.5, -0.5),
        (-0.5, 0.5),
        (0.5, 0.5),
        (0.5, -0.5),
    ], dtype='f4')

    __slots__ = (
        'width', 'height',
    )

    def __init__(
            self,
            layer,
            width,
            height,
            *,
            pos=(0, 0),
            color=(1, 1, 1, 1),
            stroke_width=1):

        self.width = width
        self.height = height

        super().__init__(
            layer,
            self._vertices(),
            pos=pos,
            color=color,
            stroke_width=stroke_width,
        )

    def _vertices(self):
        return np.copy(self.VERTS) * (self.width, self.height)


class PolyLine(Polygon):
    """An unclosed line sequence."""

    def _stroke_indices(self):
        """Indexes for drawing the line as a LINE_STRIP."""
        verts = len(self.orig_verts)
        idxs = np.arange(verts)
        last = verts - 1
        return np.array([0, *idxs, last, last])

    def _fill_indices(self):
        raise NotImplementedError(
            "Lines may not be filled."""
        )
