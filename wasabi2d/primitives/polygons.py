from unittest.mock import ANY
import math
import numpy as np
import moderngl

from ..color import convert_color
from ..allocators.vertlists import VAO
from ..sprites import Transformable

from ..vendor.earcut import earcut


class AbstractShape(Transformable):
    def _migrate_stroke(self, vao: VAO):
        """Migrate the stroke into the given VAO."""
        # TODO: dealloc from an existing VAO
        self.vao = vao
        self.lst = vao.alloc(self.segments, self.segments)
        self.lst.indexbuf[:] = self._stroke_indices()
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

    def _update(self):
        xform = self._scale @ self._rot @ self._xlate

        self.lst.vertbuf['in_vert'] = (self.orig_verts @ xform)[:, :2]
        self.lst.vertbuf['in_color'] = self._color
        self.lst.dirty = True

    def delete(self):
        """Delete this primitive."""
        self.layer._dirty.discard(self)
        self.layer.objects.discard(self)
        self.vao.free()


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
        return idxs

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
