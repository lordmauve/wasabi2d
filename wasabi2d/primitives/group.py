"""A group of other Transformables.

By grouping transformables they can be moved, rotated and scaled as one.

"""
from typing import List, Tuple

import numpy as np

from .base import Transformable


Point = Tuple[float, float]
Vector = Tuple[float, float]


class Group(Transformable):
    def __init__(
            self,
            transformables: List[Transformable],
            *,
            pos: Point = (0.0, 0.0),
            angle: float = 0.0,
            scale: float = 1.0):
        """Construct a group containing the given transformables."""
        super().__init__()
        self._objects = []
        self._result_mat = self._Transformable__xfmat.copy()
        self._inv_mat = None
        self.pos = pos
        self.angle = angle
        self.scale = scale
        self.extend(transformables)

    def extend(self, transformables: List[Transformable]):
        """Add transformables to the group."""
        for o in transformables:
            self._prepare(o)
            self._objects.append(o)

    def append(self, transformable: Transformable):
        """Add one transformable to the group."""
        self.extend([transformable])

    def _prepare(self, o):
        """Set up an object for membership of the group."""
        if o._group_xform is not None:
            raise ValueError(f"{o} is already in a group")
        elif not isinstance(o, Transformable):
            raise TypeError("Only Transformable objects can be grouped")
        o._group_xform = self._result_mat
        o._set_dirty()

    def _set_dirty(self):
        self._result_mat[:] = self._xform()
        self._inv_mat = None
        for o in self._objects:
            o._set_dirty()

    def __getitem__(self, idx: int) -> Transformable:
        """Get the transformable at the given position."""
        return self._objects[idx]

    def __delitem__(self, idx: int) -> Transformable:
        """Delete the transformable at the given position."""
        obj = self._objects.pop(idx)
        obj.delete()

    def __setitem__(self, idx: int, o: Transformable) -> Transformable:
        """Replace the object at the given index."""
        self._prepare(o)
        self._objects[idx].delete()
        self._objects[idx] = o

    def __len__(self):
        """Get the number of objects in the group."""
        return len(self._objects)

    def local_to_world(self, point: Point) -> Point:
        """Get the world position for the given local point."""
        x, y = point
        return np.array([x, y, 1]) @ self._result_mat[:, :2]

    def world_to_local(self, point: Point) -> Point:
        """Get the world position for the given local point."""
        x, y = point
        return np.array([x, y, 1]) @ self._inv[:, :2]

    def localvec_to_worldvec(self, vec: Vector) -> Vector:
        """Get the world vector for the given local vector."""
        x, y = vec
        return np.array([x, y, 0]) @ self._result_mat[:, :2]

    def worldvec_to_localvec(self, vec: Vector) -> Vector:
        """Get the world vector for the given local vector."""
        x, y = vec
        return np.array([x, y, 0]) @ self._inv[:, :2]

    @property
    def _inv(self):
        """Get the inverse transformation matrix, memoized."""
        if self._inv_mat is None:
            self._inv_mat = np.linalg.inv(self._result_mat)
        return self._inv_mat

    def delete(self):
        """Remove all primitives in the group."""
        for o in self._objects:
            o.delete()
        del self.objects[:]

    #: Alias for delete to match interface of a list
    clear = delete

    def pop(self, index: int) -> Transformable:
        """Extract a primitive from the group, leaving it in the scene.

        The primitive will have (approximately) the same world transformation
        it had within the group.
        """
        obj = self._objects.pop(index)
        mat = obj._xform()
        obj._group_xform = None
        self._factorise(obj, mat)

        # We cannot represent the skew from a non-linear scale, so this
        # operation actually does modify the matrix. If it didn't then the
        # object wouldn't be dirty.
        obj._set_dirty()
        return obj

    def explode(self) -> List[Transformable]:
        """Extract and return primitives from the group.

        This preserves the transformation for the primitives and leaves them
        in the scene.

        This group becomes empty after this operation.
        """
        # We can repeatedly call pop(), but we do it in reverse order because
        # otherwise it's quadratic
        num = len(self._objects)
        items = [None] * num
        for i in range(num - 1, -1, -1):
            items[i] = self.pop(i)
        return items

    def _factorise(self, obj, mat):
        """Assign an object's transformation properties from mat."""
        x = mat[:2, 0]
        y = mat[:2, 1]
        obj._Transformable__xfmat = mat  # sets position
        obj.angle = np.arctan2(y[0], x[0])
        obj.scale_x = np.sqrt(np.sum(x * x))
        obj.scale_y = np.sqrt(np.sum(y * y))

    def capture(self, *objects: Tuple[Transformable]):
        """Capture the given objects into the group.

        The objects will have the same transformation they had outside of the
        group.

        """
        inv = self._inv
        for o in objects:
            mat = o._xform() @ inv
            self._prepare(o)
            self._objects.append(o)
            self._factorise(o, mat)

    @classmethod
    def from_objects(cls, objects: List[Transformable], **kwargs) -> 'Group':
        """Build a group by capturing the given objects.

        Keyword arguments can be used to set the initial transform for the
        group prior to capturing the objects.
        """
        group = cls([], **kwargs)
        group.capture(*objects)
        return group
