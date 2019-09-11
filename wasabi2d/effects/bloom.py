from typing import Tuple, List
from dataclasses import dataclass

import moderngl
import numpy as np

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
BLOOM_PROG_1 = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;

uniform float weight[5] = float[] (0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);

void main()
{
    vec2 tex_offset = 1.0 / textureSize(image, 0); // gets size of single texel
    vec3 result = texture(image, uv).rgb * weight[0]; // current fragment's contribution

    for(int i = 1; i < 5; ++i)
    {
        result += texture(image, uv + vec2(0.0, tex_offset.y * i)).rgb * weight[i];
        result += texture(image, uv - vec2(0.0, tex_offset.y * i)).rgb * weight[i];
    }
    f_color = vec4(result, 1);
}

"""


# Second pass, perform horizontal blur and composite original
BLOOM_PROG_2 = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D vblurred;

uniform float weight[5] = float[] (0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);

void main()
{
    vec2 tex_offset = 1.0 / textureSize(vblurred, 0); // gets size of single texel
    vec3 result = texture(vblurred, uv).rgb * weight[0]; // current fragment's contribution


    for(int i = 1; i < 5; ++i)
    {
        result += texture(vblurred, uv + vec2(tex_offset.x * i, 0.0)).rgb * weight[i];
        result += texture(vblurred, uv - vec2(tex_offset.x * i, 0.0)).rgb * weight[i];
    }
    f_color = vec4(result, 1);
}

"""


@dataclass
class Bloom:
    """A light bloom effect."""
    ctx: moderngl.Context
    shadermgr: 'wasabi2d.layers.ShaderManager'
    threshold: float = 1.0
    radius: float = 10.0

    camera: 'wasabi2d.scene.Camera' = None
    _pass1: PostprocessPass = None
    _pass2: PostprocessPass = None
    _fb1: moderngl.Framebuffer = None
    _fb2: moderngl.Framebuffer = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._fb1, = camera._get_temporary_fbs(1, 'f2')
        self._thresholded = self.ctx.framebuffer([
            self.ctx.texture(
                (camera.width // 8, camera.height // 8),
                4,
                dtype='f2'
            )
        ])
        self._fb2 = self.ctx.framebuffer([
            self.ctx.texture(
                (camera.width // 8, camera.height),
                4,
                dtype='f2'
            )
        ])
        self._threshold_pass = PostprocessPass(
            self.ctx,
            self.shadermgr,
            THRESHOLD_PROG,
        )
        self._pass1 = PostprocessPass(
            self.ctx,
            self.shadermgr,
            BLOOM_PROG_1
        )
        self._pass2 = PostprocessPass(
            self.ctx,
            self.shadermgr,
            BLOOM_PROG_2
        )
        self._copy = self._mkpass(COPY_PROG)

    def _mkpass(self, shader):
        return PostprocessPass(self.ctx, self.shadermgr, shader)

    def enter(self, t, dt):
        self._fb1.use()
        self._fb1.clear()

    def exit(self, t, dt):
        self._thresholded.use()
        self._thresholded.clear()
        self._threshold_pass.render(image=self._fb1)

        self._fb2.use()
        self._fb2.clear()
        self._pass1.render(
            image=self._thresholded,
        )
        self.ctx.screen.use()

        self._copy.render(image=self._fb1)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE
        self._pass2.render(
            vblurred=self._fb2,
        )
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
