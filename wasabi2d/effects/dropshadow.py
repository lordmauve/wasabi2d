"""A drop-shadow effect.

Very similar to the blur effect (wasabi2d.effects.blur) but composite
the original image on top.

"""
from typing import Tuple
from dataclasses import dataclass

import moderngl

from ..shaders import bind_framebuffer
from .base import PostprocessPass
from .blur import Blur


@dataclass
class Dropshadow:
    """A drop shadow effect."""
    ctx: moderngl.Context
    radius: float = 10.0
    offset: Tuple[float, float] = (1.0, 1.0)
    opacity: float = 1.0

    camera: 'wasabi2d.scene.Camera' = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._fb = camera._make_fb('f2')
        self.blur = Blur(
            self.ctx,
            self.radius
        )
        self.blur._set_camera(camera)
        self.blur._outer_fb = self._fb
        self._composite = PostprocessPass(
            self.ctx,
            'postprocess/dropshadow_composite'
        )

    def draw(self, draw_layer):
        self.blur.radius = self.radius
        self._fb.clear()
        with bind_framebuffer(self.ctx, self._fb):
            self.blur.draw(draw_layer)
        self._composite.render(
            blurred=self._fb,
            image=self.blur._fb1,
            offset=self.offset,
            opacity=self.opacity,
        )

