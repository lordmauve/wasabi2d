"""Base class for effects that simply apply a color matrix."""
from dataclasses import dataclass
import abc

import moderngl
import numpy as np

from ..shaders import bind_framebuffer
from .base import PostprocessPass


@dataclass
class BaseMatrix(metaclass=abc.ABCMeta):
    ctx: moderngl.Context

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera

        self._color_mat = PostprocessPass(
            self.ctx,
            'postprocess/color_matrix'
        )

    @abc.abstractmethod
    def get_matrix(self) -> np.ndarray:
        """Get the matrix to draw.

        The matrix should be (4x4).
        """

    def draw(self, draw_layer):
        """Subclasses should implement this to pass the matrix to draw."""
        with self.camera.temporary_fb() as fb:
            with bind_framebuffer(self.ctx, fb, clear=True):
                draw_layer()

            self._color_mat.render(
                image=fb,
                color_matrix=self.get_matrix(),
            )
