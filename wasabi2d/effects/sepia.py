"""Convert colours to sepia."""
from dataclasses import dataclass

import numpy as np

from .base_matrix import BaseMatrix


SRC_ARR = np.array([
    [0.393, 0.769, 0.189],
    [0.349, 0.686, 0.168],
    [0.272, 0.534, 0.131],
])

DEST_ARR = np.array([
    [0.607, -0.769, -0.189],
    [-0.349, 0.314, -0.168],
    [-0.272, -0.534, 0.869],
])


@dataclass
class Sepia(BaseMatrix):
    """A sepia effect."""
    amount: float = 1.0

    def get_matrix(self):
        matrix = np.identity(4, dtype=np.float32)
        matrix[:3, :3] = (1 - self.amount) * DEST_ARR
        matrix[:3, :3] += SRC_ARR
        return matrix
