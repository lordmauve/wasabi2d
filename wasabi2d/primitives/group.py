"""A group of other Transformables.

By grouping transformables they can be moved, rotated and scaled as one.

"""
from typing import List, Tuple

import numpy as np

from .base import Transformable


Point = Tuple[float, float]


class Group(Transformable):
    def __init__(
            self,
            transformables: List[Transformable],
            *,
            pos: Point = (0.0, 0.0),
            angle: float = 0.0,
            scale: float = 1.0,
            ):
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
            if o._group_xform is not None:
                raise ValueError(f"{o} is already in a group")
            elif not isinstance(o, Transformable):
                raise TypeError("Only Transformable objects can be grouped")
            o._group_xform = self._result_mat
            self._objects.append(o)

    def _set_dirty(self):
        self._result_mat[:] = self._xform()
        self._inv_mat = None
        for o in self._objects:
            o._set_dirty()

    def __getitem__(self, idx):
        """Get the transformable at the given position."""
        return self._objects[idx]

    def __len__(self):
        """Get the number of objects in the group."""
        return len(self._objects)

    def local_to_world(self, point: Point) -> Point:
        """Get the world position for the given local point."""
        x, y = point
        return self._result_mat[:2, :] @ np.array([x, y, 1])

    def world_to_local(self, point: Point) -> Point:
        """Get the world position for the given local point."""
        x, y = point
        if self._inv_mat is None:
            self._inv_mat = np.linalg.inv(self._result_mat)[:2, :]
        return self._inv_mat @ np.array([x, y, 1])
