import numpy as np

from functools import partial

from ..color import convert_color
from ..allocators.vertlists import VAO
from ..rect import ZRect
from ..descriptors import CallbackProp

#: Return an identity transformation matrix
identity = partial(np.identity, dtype=np.float32)


def bounds_from_verts(vertices: np.ndarray) -> ZRect:
    """Given an array of vertices, get the bounds of the object."""
    # Ensure we only have 2D vertices
    vertices = vertices[:, :2]

    # Calculate the bounds
    mins = np.min(vertices, axis=0)
    maxs = np.max(vertices, axis=0)
    return ZRect(mins, maxs - mins)


class Bounds:
    """Descriptor for a property that returns bounds based on vertices.

    We compile an expression to access the vertices in order to be faster and
    save code.

    """

    def __init__(self, expr="self.lst.vertbuf['in_vert']"):
        self.getter = eval(f"lambda self: {expr}")

    def __get__(self, inst, cls=None):
        return bounds_from_verts(self.getter(inst))


class Transformable:
    _angle = 0
    _group_xform = None

    def __init__(self):
        super().__init__()
        self._scale = identity(2)
        self._rot = identity(2)
        self.__xfmat = identity(3)
        self.__build_mat = partial(
            np.matmul,
            self._scale,
            self._rot,
            out=self.__xfmat[:2, :2]
        )

    @property
    def pos(self):
        return self.__xfmat[2][:2]

    @pos.setter
    def pos(self, v):
        assert len(v) == 2
        self.__xfmat[2][:2] = v
        self._set_dirty()

    @property
    def x(self):
        return self.__xfmat[2, 0]

    @x.setter
    def x(self, v):
        self.__xfmat[2, 0] = v
        self._set_dirty()

    @property
    def y(self):
        return self.__xfmat[2, 1]

    @y.setter
    def y(self, v):
        self.__xfmat[2, 1] = v
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
    def scale_x(self):
        return self._scale[0, 0]

    @scale_x.setter
    def scale_x(self, v):
        self._scale[0, 0] = v
        self._set_dirty()

    @property
    def scale_y(self):
        return self._scale[1, 1]

    @scale_y.setter
    def scale_y(self, v):
        self._scale[1, 1] = v
        self._set_dirty()

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, theta):
        assert np.isscalar(theta)
        s = np.sin(theta)
        c = np.cos(theta)
        self._rot[:] = [
            [c, s],
            [-s, c],
        ]
        self._angle = theta
        self._set_dirty()

    def _xform(self):
        self.__build_mat()
        if self._group_xform is not None:
            return self.__xfmat @ self._group_xform
        return self.__xfmat


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

    def _migrate_stroke(self, vao: VAO):
        """Migrate the stroke into the given VAO."""
        # TODO: dealloc from an existing VAO
        idxs = self._stroke_indices()
        self.vao = vao
        self.lst = vao.alloc(len(self.orig_verts), len(idxs))
        self.lst.indexbuf[:] = idxs
        self.lst.indexbuf += self.lst.vertoff.start
        self._update()

    def _migrate_fill(self, vao: VAO):
        """Migrate the fill into the given VAO."""
        # TODO: dealloc from an existing VAO
        idxs = self._fill_indices()
        self.vao = vao
        self.lst = vao.alloc(len(self.orig_verts), len(idxs))
        self.lst.indexbuf[:] = idxs
        self.lst.indexbuf += self.lst.vertoff.start
        self._update()

    def _set_dirty(self):
        self.layer._dirty.add(self)

    _stroke_width = 1.0
    stroke_width = CallbackProp(_set_dirty)
    bounds = Bounds()

    def _update(self):
        xform = self._xform()

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
