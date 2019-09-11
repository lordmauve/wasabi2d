"""An effect where we keep trails from previous frames."""
from typing import Tuple, List
from dataclasses import dataclass

import moderngl

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
    shadermgr: 'wasabi2d.layers.ShaderManager'
    fade: float = 0.9

    camera: 'wasabi2d.scene.Camera' = None
    _pass: PostprocessPass = None
    _fb: moderngl.Framebuffer = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._fb = camera._make_fb('f2')
        self._fade_pass = PostprocessPass(
            self.ctx,
            self.shadermgr,
            FADE_PROG,
            send_uvs=False
        )
        self._composite_pass = PostprocessPass(
            self.ctx,
            self.shadermgr,
            COMPOSITE_PROG,
        )

    def enter(self, t, dt):
        self._fb.use()
        self._fade_pass.render(
            fade=self.fade,
            dt=dt
        )

    def exit(self, t, dt):
        self.ctx.screen.use()
        self._composite_pass.render(fb=self._fb)
