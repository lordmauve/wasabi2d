"""An effect where we keep trails from previous frames."""
from typing import Tuple, List
from dataclasses import dataclass

import moderngl

from ..clock import Clock, default_clock
from ..shaders import bind_framebuffer
from .base import PostprocessPass


FADE_PROG = """ \
#version 330 core

out vec4 f_color;

uniform float fade;
uniform float dt;

void main()
{
    f_color = vec4(0, 0, 0, 1.0 - pow(fade, dt));
}

"""


COMPOSITE_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D fb;

void main()
{
    f_color = texture(fb, uv);
}

"""


@dataclass
class Trails:
    """A trails effect."""
    ctx: moderngl.Context
    fade: float = 0.9
    clock: Clock = default_clock

    camera: 'wasabi2d.scene.Camera' = None
    _pass: PostprocessPass = None
    _fb: moderngl.Framebuffer = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._fb = camera._make_fb('f2')
        self._fade_pass = PostprocessPass(
            self.ctx,
            FADE_PROG,
            send_uvs=False
        )
        self._composite_pass = PostprocessPass(
            self.ctx,
            COMPOSITE_PROG,
        )

    def draw(self, draw_layer):
        with bind_framebuffer(self.ctx, self._fb):
            self._fade_pass.render(
                fade=self.fade,
                dt=self.clock.dt  # FIXME: do this operation on tick
            )
            draw_layer()
        self._composite_pass.render(fb=self._fb)
