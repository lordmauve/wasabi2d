from typing import Tuple, List
from dataclasses import dataclass

import moderngl
import numpy as np

from ..shaders import bind_framebuffer, blend_func
from .base import PostprocessPass


def gaussian(x, mu, sig):
    """Calculate a gaussian function."""
    return np.exp(-np.power(x - mu, 2.) / (2 * np.power(sig, 2.)))


THRESHOLD_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;

void main()
{
    vec4 in_col = texture(image, uv);
    float lum = dot(vec3(0.3, 0.6, 0.1), in_col.rgb) * in_col.a;
    f_color = in_col * pow(lum, 2);
}

"""


COPY_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D image;

void main()
{
    f_color = texture(image, uv);
}
"""

# Shader code adapted from https://learnopengl.com/Advanced-Lighting/Bloom
# First pass, blur vertically
BLUR_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;
uniform sampler2D gauss_tex;
uniform float radius;
uniform vec2 blur_direction;


float gauss(float off) {
    return texture(gauss_tex, vec2(abs(off / radius), 0)).r;
}


void main()
{
    vec2 tex_offset = 1.0 / textureSize(image, 0); // gets size of single texel
    vec3 result = texture(image, uv).rgb; // current fragment's contribution

    vec2 lookup_stride = tex_offset * blur_direction;
    float weight_sum = 1.0;
    float weight;
    int irad = int(radius);
    for(int i = 1; i < irad; ++i)
    {
        weight = gauss(i);
        weight_sum += i * 2;
        result += texture(image, uv + lookup_stride * i).rgb * weight;
        result += texture(image, uv - lookup_stride * i).rgb * weight;
    }
    f_color = vec4(result / radius * 2, 1);
}

"""


@dataclass
class Bloom:
    """A light bloom effect."""
    ctx: moderngl.Context
    threshold: float = 1.0
    radius: float = 10.0

    camera: 'wasabi2d.scene.Camera' = None
    _blur: PostprocessPass = None
    _fb1: moderngl.Framebuffer = None
    _fb2: moderngl.Framebuffer = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._fb1, = camera._get_temporary_fbs(1, 'f2')
        self._thresholded = camera._make_fb('f2', div_x=4, div_y=4)
        gauss = gaussian(np.arange(256), 0, 90).astype('f4')
        self._gauss_tex = self.ctx.texture((256, 1), 1, data=gauss, dtype='f4')
        self._fb2 = camera._make_fb('f2', div_x=4)
        self._threshold_pass = PostprocessPass(
            self.ctx,
            THRESHOLD_PROG,
        )
        self._blur = PostprocessPass(
            self.ctx,
            BLUR_PROG
        )
        self._copy = self._mkpass(COPY_PROG)

    def _mkpass(self, shader):
        return PostprocessPass(self.ctx, shader)

    def draw(self, draw_layer):
        with bind_framebuffer(self.ctx, self._fb1, clear=True):
            draw_layer()

        with bind_framebuffer(self.ctx, self._thresholded, clear=True):
            self._threshold_pass.render(image=self._fb1)

        with bind_framebuffer(self.ctx, self._fb2, clear=True):
            self._blur.render(
                image=self._thresholded,
                blur_direction=(0, 1),
                radius=self.radius,
                gauss_tex=self._gauss_tex,
            )

        self._copy.render(image=self._fb1)
        with blend_func(self.ctx, moderngl.SRC_ALPHA, moderngl.ONE):
            self._blur.render(
                image=self._fb2,
                blur_direction=(1, 0),
                radius=self.radius,
                gauss_tex=self._gauss_tex,
            )
