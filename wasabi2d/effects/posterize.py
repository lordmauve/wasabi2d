"""Posterize, a colour reduction effect."""
from dataclasses import dataclass

import moderngl

from ..shaders import bind_framebuffer
from .base import PostprocessPass


@dataclass
class Posterize:
    ctx: moderngl.Context
    levels: int = 2
    gamma: float = 0.7

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._posterize = PostprocessPass(self.ctx, 'postprocess/posterize')

    def draw(self, draw_layer):
        """Subclasses should implement this to pass the matrix to draw."""
        with self.camera.temporary_fb() as fb:
            with bind_framebuffer(self.ctx, fb, clear=True):
                draw_layer()

            self._posterize.render(
                image=fb,
                levels=self.levels,
                gamma=self.gamma,
            )
