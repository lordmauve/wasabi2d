from dataclasses import dataclass

import moderngl

from ..shaders import blend_func


@dataclass
class Additive:
    ctx: moderngl.Context

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Nothing to do here."""

    def draw(self, draw_layer):
        """Draw the wrapped effects with additive blending."""
        with blend_func(
            self.ctx,
            src=moderngl.SRC_ALPHA,
            dest=moderngl.ONE,
            src_a=moderngl.ONE,
            dest_a=moderngl.ONE,
        ):
            draw_layer()
