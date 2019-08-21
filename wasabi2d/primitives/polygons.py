from unittest.mock import ANY
import numpy as np

from ..color import convert_color
from ..allocators.vertlists import VAO
from ..sprites import Colorable, Transformable

from ..vendor.earcut import earcut


class AbstractShape(Colorable, Transformable):
    _stroke_width = 1.0

    def _migrate_stroke(self, vao: VAO):
        """Migrate the stroke into the given VAO."""
        # TODO: dealloc from an existing VAO
        idxs = self._stroke_indices()
        self.vao = vao
        self.lst = vao.alloc(len(self.orig_verts), len(idxs))
        self.lst.indexbuf[:] = idxs
        self._update()

    def _migrate_fill(self, vao: VAO):
        """Migrate the fill into the given VAO."""
        # TODO: dealloc from an existing VAO
        idxs = self._fill_indices()
        self.vao = vao
        self.lst = vao.alloc(len(self.orig_verts), len(idxs))
        self.lst.indexbuf[:] = idxs
        self._update()

    def _set_dirty(self):
        self.layer._dirty.add(self)

    @property
    def stroke_width(self):
        """Get the stroke width, in pixels."""
        return self._stroke_width

    @stroke_width.setter
    def stroke_width(self, v):
        """Set the stroke width in pixels."""
        self._stroke_width = v
        self._set_dirty()

    def _update(self):
        xform = self._scale @ self._rot @ self._xlate

        np.matmul(
            self.orig_verts,
            xform[:, :2],
            self.lst.vertbuf['in_vert']
        )
        self.lst.vertbuf['in_color'] = self._color
        if 'in_linewidth' in self.lst.vertbuf.dtype.fields:
            self.lst.vertbuf['in_linewidth'] = self._stroke_width
        self.lst.dirty = True

    def delete(self):
        """Delete this primitive."""
        self.layer._dirty.discard(self)
        self.layer.objects.discard(self)
        self.vao.free(self.lst)
        self.lst = None
        self.layer = None


class Polygon(AbstractShape):
    """An arbitrary polygon."""

    def __init__(
            self,
            layer,
            vertices,
            *,
            pos=(0, 0),
            color=(1, 1, 1, 1)):

        verts = np.array(vertices, dtype='f4')
        if verts.shape != (ANY, 2):
            raise ValueError(
                f"Unsupported vertex shape {verts.shape}, expected (*, 2)"
            )

        super().__init__()
        self.layer = layer
        self.pos = pos

        self.orig_verts = np.ones((len(verts), 3), dtype='f4')
        self.orig_verts[:, :2] = verts

        self._color = convert_color(color)
        self._set_dirty()

    def _stroke_indices(self):
        """Indexes for drawing the stroke as a LINE_STRIP."""
        verts = len(self.orig_verts)
        idxs = np.linspace(
            0,
            verts,
            verts + 1,
            dtype='i4'
        )
        idxs[-1] = 0
        return idxs[[-1, *range(verts), 0, 1, 2]]

    def _fill_indices(self):
        """Indexes for drawing the fill as TRIANGLES."""
        verts = self.orig_verts[:, :2].reshape((-1))
        idxs = earcut(verts)
        return np.array(idxs, dtype='i4')


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
            color=(1, 1, 1, 1)):

        self.width = width
        self.height = height

        super().__init__(
            layer,
            self._vertices(),
            pos=pos,
            color=color
        )

    def _vertices(self):
        return np.copy(self.VERTS) * (self.width, self.height)

    @property
    def left(self):
        return self.pos[0] - self.width / 2

    @left.setter
    def left(self, v):
        self.pos[0] = v + self.width / 2
        self._set_dirty()

    @property
    def right(self):
        return self.pos[0] + self.width / 2

    @right.setter
    def right(self, v):
        self.pos[0] = v - self.width / 2
        self._set_dirty()

    @property
    def top(self):
        return self.pos[1] - self.height / 2

    @top.setter
    def top(self, v):
        self.pos[1] = v + self.height / 2
        self._set_dirty()

    @property
    def bottom(self):
        return self.pos[1] + self.height / 2

    @bottom.setter
    def bottom(self, v):
        self.pos[1] = v - self.height / 2
        self._set_dirty()

    @property
    def centerx(self):
        return self.pos[0]

    @property
    def centery(self):
        return self.pos[1]
