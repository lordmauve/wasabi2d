from dataclasses import dataclass

import moderngl
import numpy as np

from ..shaders import bind_framebuffer, blend_func
from .base import PostprocessPass


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
//uniform sampler2D gauss_tex;
uniform float radius;
uniform vec2 blur_direction;

uniform float threshold;
uniform float alpha;


float gauss(float off) {
    float x = off / radius * 2;
    return exp(x * x / -2.0);
}


vec3 sample(vec2 pos) {
    vec3 val = texture(image, uv + pos).rgb;
    float intensity = (val.r + val.g + val.b) / 3;
    return val * step(threshold, intensity);
}


void main()
{
    vec2 tex_offset = 1.0 / textureSize(image, 0); // gets size of single texel
    vec3 result = texture(image, uv).rgb; // current fragment's contribution

    vec2 lookup_stride = tex_offset * blur_direction;
    float weight;
    int irad = int(radius);
    for(int i = 1; i <= irad; ++i)
    {
        weight = gauss(i);
        result += sample(lookup_stride * i) * weight;
        result += sample(lookup_stride * -i) * weight;
    }
    f_color = vec4(result / radius * 2, alpha);
}

"""


@dataclass
class Bloom:
    """A light bloom effect."""
    ctx: moderngl.Context
    threshold: float = 0.3
    radius: float = 10.0
    intensity: float = 0.5

    camera: 'wasabi2d.scene.Camera' = None
    _blur: PostprocessPass = None
    _fb1: moderngl.Framebuffer = None
    _fb2: moderngl.Framebuffer = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
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
        with self.camera.temporary_fb('f1') as fb1:
            with bind_framebuffer(self.ctx, fb1, clear=True):
                draw_layer()

            with self.camera.temporary_fb() as fb2:
                with bind_framebuffer(self.ctx, fb2):
                    with blend_func(self.ctx, moderngl.ONE, moderngl.ZERO):
                        self._blur.render(
                            image=fb1,
                            threshold=self.threshold,
                            blur_direction=(0, 1),
                            radius=self.radius,
                            alpha=1.0
                        )

                self._copy.render(image=fb1)
                with blend_func(self.ctx, moderngl.SRC_ALPHA, moderngl.ONE):
                    self._blur.render(
                        image=fb2,
                        threshold=0.0,
                        blur_direction=(1, 0),
                        radius=self.radius,
                        alpha=self.intensity
                    )
