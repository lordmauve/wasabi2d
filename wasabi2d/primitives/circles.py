import math
import numpy as np
from ..allocators.vertlists import VertList
from ..sprites import Transformable


class Circle(Transformable):
    """A circle drawn with lines."""

    def __init__(
            self,
            pos=(0, 0),
            radius=100,
            color=(1, 1, 1, 1),
            segments=None):
        super().__init__()
        self.segments = segments or round(radius * math.pi)
        self.pos = pos
        self._radius = radius

        theta = np.linspace(0, 2 * np.pi, self.segments)
        self.orig_verts = np.hstack([
            self.radius * np.cos(theta),
            self.radius * np.sin(theta),
            1
        ])
        self.color = color
