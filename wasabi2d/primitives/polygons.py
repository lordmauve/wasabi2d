import numpy as np

try:
    from wasabigeom import triangulate
except ImportError:
    # Keep installations with older wasabi-geom releases working.
    triangulate = None

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

    def _fill_indices_earstrip(self):
        """Use Earstrip for simple polygons; retain Earcut's repair behaviour.

        The native binding returns independent uint32 storage. NumPy views that
        storage without copying, including when orig_verts has a 3-float stride.
        """
        try:
            idxs = triangulate(self.orig_verts[:, :2])
        except ValueError:
            # Earstrip's index-only API refuses polygons it cannot cut exactly.
            # Earcut historically accepts some non-simple polygons, so preserve
            # that path instead of changing the Polygon rendering contract.
            if mapbox_earcut:
                return self._fill_indices_mapbox_earcut()
            return self._fill_indices_earcut()
        return np.asarray(idxs).reshape(-1)

    def _fill_indices_mapbox_earcut(self):
        """Indexes for drawing the fill as TRIANGLES.

        This version uses the mapbox_earcut C++ library. It remains the fallback
        for older wasabi-geom releases and polygons Earstrip refuses.

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

    if triangulate is not None:
        _fill_indices = _fill_indices_earstrip
    elif mapbox_earcut:
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

    @property
    def colors(self):
        """Get the colour per vertex."""
        if self._color.shape == (4,):
            return np.array(
                [self._color] * len(self.orig_verts),
                dtype=np.float32
            )
        else:
            return self._color

    @colors.setter
    def colors(self, v):
        """Set the per-vertex colour."""
        self._color = v
        self._set_dirty()

    def _fill_indices(self):
        raise NotImplementedError(
            "Lines may not be filled."""
        )
