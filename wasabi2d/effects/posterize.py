"""Posterize, a colour reduction effect."""
from dataclasses import dataclass

import moderngl

from ..shaders import bind_framebuffer
from .base import PostprocessPass


POSTER_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D image;
uniform int levels;
uniform float gamma;

vec3 posterize(vec3 color) {
    vec3 gammac = pow(color, vec3(gamma, gamma, gamma));
    vec3 post = floor(gammac * levels + vec3(0.5, 0.5, 0.5)) / levels;
    float inv_g = 1.0 / gamma;
    return pow(post, vec3(inv_g, inv_g, inv_g));
}

void main()
{
    vec4 frag = texture(image, uv);
    if (frag.a < 1e-6) {
        discard;
    }
    f_color = vec4(posterize(frag.rgb / frag.a), frag.a);
}
"""


@dataclass
class Posterize:
    ctx: moderngl.Context
    levels: int = 2
    gamma: float = 0.7

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._posterize = PostprocessPass(
            self.ctx,
            POSTER_PROG
        )

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
