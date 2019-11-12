"""Convert colours to greyscale."""
from dataclasses import dataclass

import numpy as np

from .base_matrix import BaseMatrix


SRC_ARR = np.array([
    [0.2126, 0.7152, 0.0722],
] * 3)

DEST_ARR = np.array([
    [0.7874, -0.7152, -0.0722],
    [-0.2126, 0.2848, -0.0722],
    [-0.2126, -0.7152, 0.9278],
])


@dataclass
class Greyscale(BaseMatrix):
    """A sepia effect."""
    amount: float = 1.0

    def get_matrix(self):
        matrix = np.identity(4, dtype=np.float32)
        matrix[:3, :3] = (1 - self.amount) * DEST_ARR
        matrix[:3, :3] += SRC_ARR
        return matrix
