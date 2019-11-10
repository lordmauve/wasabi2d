"""An effect where we keep trails from previous frames."""
from dataclasses import dataclass

import moderngl

from ..clock import Clock, default_clock
from ..shaders import bind_framebuffer, blend_func
from .base import PostprocessPass


FADE_PROG = """ \
#version 330 core

out vec4 f_color;

uniform float fade;

void main()
{
    f_color = vec4(0, 0, 0, fade);
}

"""


COMPOSITE_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;

uniform float alpha;
uniform sampler2D fb;

void main()
{
    vec4 frag = texture(fb, uv);
    f_color = vec4(frag.rgb, frag.a * alpha);
}

"""


@dataclass
class Trails:
    """A trails effect."""
    ctx: moderngl.Context
    fade: float = 0.9
    alpha: float = 1.0
    clock: Clock = default_clock

    camera: 'wasabi2d.scene.Camera' = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._trails_buf = camera._make_fb('f4')
        self._fade_pass = PostprocessPass(
            self.ctx,
            FADE_PROG,
            send_uvs=False
        )
        self._composite_pass = PostprocessPass(
            self.ctx,
            COMPOSITE_PROG,
        )
        self.t = self.clock.t

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
