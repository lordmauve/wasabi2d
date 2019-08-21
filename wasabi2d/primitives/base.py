import numpy as np
from pyrr import vector3, matrix33

from ..color import convert_color
from ..allocators.vertlists import VAO


Z = vector3.create_unit_length_z()


def identity():
    """Return an identity transformation matrix."""
    return np.identity(3, dtype='f4')


class Transformable:
    _angle = 0

    def __init__(self):
        super().__init__()
        self._scale = identity()
        self._rot = identity()
        self._xlate = identity()

    @property
    def pos(self):
        return self._xlate[2][:2]

    @pos.setter
    def pos(self, v):
        assert len(v) == 2
        self._xlate[2][:2] = v
        self._set_dirty()

    @property
    def x(self):
        return self._xlate[2, 0]

    @x.setter
    def x(self, v):
        self._xlate[2, 0] = v
        self._set_dirty()

    @property
    def y(self):
        return self._xlate[2, 1]

    @y.setter
    def y(self, v):
        self._xlate[2, 1] = v
        self._set_dirty()

    @property
    def scale(self):
        p = np.product(np.diagonal(self._scale))
        return np.copysign(np.sqrt(abs(p)), p)

    @scale.setter
    def scale(self, v):
        self._scale[0, 0] = self._scale[1, 1] = v
        self._set_dirty()

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, theta):
        assert isinstance(theta, (int, float))
        self._rot = matrix33.create_from_axis_rotation(Z, theta, dtype='f4')
        self._angle = theta
        self._set_dirty()


class Colorable:
    """Mix-in for a primitive that has a 4-component color value."""

    def __init__(self):
        super().__init__()
        self._color = np.ones(4, dtype='f4')

    @property
    def color(self):
        return tuple(self._color)

    @color.setter
    def color(self, v):
        self._color[:] = convert_color(v)
        self._set_dirty()


class AbstractShape(Colorable, Transformable):
    """Base class for polygonal shapes."""
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



