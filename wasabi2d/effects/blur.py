"""Separable Gaussian blur."""
from dataclasses import dataclass

import moderngl

from ..shaders import bind_framebuffer
from .base import PostprocessPass


# Shader code adapted from https://learnopengl.com/Advanced-Lighting/Bloom
# First pass, blur vertically
BLUR_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;
uniform float radius;
uniform vec2 blur_direction;


float gauss(float off) {
    float x = off / radius * 2;
    return exp(x * x / -2.0);
}


void main()
{
    vec2 tex_offset = 1.0 / textureSize(image, 0); // gets size of single texel
    vec4 result = texture(image, uv); // current fragment's contribution

    vec2 lookup_stride = tex_offset * blur_direction;
    float weight_sum = 1.0;
    float weight;
    int irad = int(ceil(radius));
    for(int i = 1; i < irad; ++i)
    {
        weight = gauss(i);
        weight_sum += weight * 2;
        result += texture(image, uv + lookup_stride * i) * weight;
        result += texture(image, uv - lookup_stride * i) * weight;
    }
    f_color = result / weight_sum;
}

"""


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
            BLUR_PROG
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
