"""Separable Gaussian blur."""
from dataclasses import dataclass

import moderngl

from ..shaders import bind_framebuffer
from .base import PostprocessPass


@dataclass
class Blur:
    """A light bloom effect."""
    ctx: moderngl.Context
    radius: float = 10.0

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._outer_fb = self.ctx.screen
        self._blur = PostprocessPass(
            self.ctx,
            'postprocess/blur',
        )

    def draw(self, draw_layer):
        with self.camera.temporary_fbs(2, 'f2') as (fb1, fb2):
            with bind_framebuffer(self.ctx, fb1, clear=True):
                draw_layer()

            # Hold onto this for the drop shadow effect to use.
            # This is very much cheating.
            self._fb1 = fb1

            with bind_framebuffer(self.ctx, fb2, clear=True):
                self._blur.render(
                    image=fb1,
                    blur_direction=(0, 1),
                    radius=self.radius,
                )

            self._blur.render(
                image=fb2,
                blur_direction=(1, 0),
                radius=self.radius,
            )
