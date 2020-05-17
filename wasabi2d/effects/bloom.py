from dataclasses import dataclass

import moderngl

from ..shaders import bind_framebuffer, blend_func
from .base import PostprocessPass


@dataclass
class Bloom:
    """A light bloom effect."""
    ctx: moderngl.Context
    gamma: float = 1.0
    radius: float = 10.0
    intensity: float = 0.5

    camera: 'wasabi2d.scene.Camera' = None
    _blur: PostprocessPass = None
    _fb1: moderngl.Framebuffer = None
    _fb2: moderngl.Framebuffer = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._blur = PostprocessPass(
            self.ctx,
            'postprocess/bloom_blur'
        )
        self._copy = PostprocessPass(self.ctx, 'postprocess/copy')

    def draw(self, draw_layer):
        with self.camera.temporary_fb('f1') as fb1:
            with bind_framebuffer(self.ctx, fb1, clear=True):
                draw_layer()

            with self.camera.temporary_fb() as fb2:
                with bind_framebuffer(self.ctx, fb2):
                    with blend_func(self.ctx, moderngl.ONE, moderngl.ZERO):
                        self._blur.render(
                            image=fb1,
                            gamma=self.gamma,
                            blur_direction=(0, 1),
                            radius=self.radius,
                            alpha=1.0
                        )

                self._copy.render(image=fb1)
                with blend_func(self.ctx, moderngl.SRC_ALPHA, moderngl.ONE):
                    self._blur.render(
                        image=fb2,
                        gamma=1e-6,
                        blur_direction=(1, 0),
                        radius=self.radius,
                        alpha=self.intensity
                    )
