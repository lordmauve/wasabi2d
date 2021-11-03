"""An outline effect."""
from typing import Tuple
from dataclasses import dataclass

import moderngl

from ..shaders import bind_framebuffer
from .base import PostprocessPass


@dataclass
class Outline:
    """A screen-space outline effect."""

    ctx: moderngl.Context
    color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    camera: 'wasabi2d.scene.Camera' = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._shader = PostprocessPass(self.ctx, 'postprocess/outline')

    def draw(self, draw_layer):
        """Subclasses should implement this to pass the matrix to draw."""
        with self.camera.temporary_fb() as fb:
            with bind_framebuffer(self.ctx, fb, clear=True):
                draw_layer()

            self._shader.render(
                image=fb,
                color=self.color,
            )

