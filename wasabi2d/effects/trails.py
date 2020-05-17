"""An effect where we keep trails from previous frames."""
from dataclasses import dataclass

import moderngl

from ..clock import Clock, default_clock
from ..shaders import bind_framebuffer, blend_func
from .base import PostprocessPass


@dataclass
class Trails:
    """A trails effect."""
    ctx: moderngl.Context
    fade: float = 0.9
    alpha: float = 1.0
    clock: Clock = default_clock

    camera: 'wasabi2d.scene.Camera' = None
    _trails_buf: moderngl.Framebuffer = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._trails_buf = camera._make_fb('f4')
        self._fade_pass = PostprocessPass(
            self.ctx,
            'postprocess/trails_fade',
            send_uvs=False
        )
        self._composite_pass = PostprocessPass(
            self.ctx,
            'postprocess/trails_composite',
        )
        self.t = self.clock.t

    def __del__(self):
        if self._trails_buf:
            self._trails_buf.release()

    def draw(self, draw_layer):
        dt = self.clock.t - self.t
        self.t = self.clock.t

        with self.camera.temporary_fbs(1, 'f2') as (tmp,):
            with blend_func(self.ctx, 'a', '1-a', '1', '1-a'):
                with bind_framebuffer(self.ctx, tmp, clear=True):
                    draw_layer()

                self._composite_pass.render(
                    fb=self._trails_buf,
                    alpha=self.alpha,
                )
                self._composite_pass.render(
                    fb=tmp,
                    alpha=1.0
                )

            with bind_framebuffer(self.ctx, self._trails_buf):
                with blend_func(self.ctx, 'a', '1-a', '1', '1-a'):
                    self._composite_pass.render(
                        fb=tmp,
                        alpha=1.0
                    )
                with blend_func(self.ctx, 0, 1, 0, 'a'):
                    self._fade_pass.render(
                        fade=self.fade ** dt
                    )
