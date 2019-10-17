"""Pixellate by averaging pixel values."""
from dataclasses import dataclass

import moderngl

from .base import PostprocessPass


AVERAGE_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;
uniform int pxsize;
uniform vec2 blur_direction;
uniform vec2 uvscale;


void main()
{
    vec2 tex_offset = 1.0 / textureSize(image, 0); // gets size of single texel
    vec4 result = vec4(0, 0, 0, 0);

    vec2 inuv = uv * uvscale;  // uv in the input image
    vec2 lookup_stride = tex_offset * blur_direction;
    for(int i = 0; i < pxsize; i++) {
        float off = i - pxsize / 2;
        result += texture(image, inuv + lookup_stride * off);
    }
    f_color = result / pxsize;
}

"""


COPY_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D image;
uniform int pxsize;

void main()
{
    f_color = texture(image, uv / pxsize);
}
"""




@dataclass
class Pixellate:
    """A pixellation effect."""

    ctx: moderngl.Context
    shadermgr: 'wasabi2d.layers.ShaderManager'
    pxsize: int = 10

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._outer_fb = self.ctx.screen
        self._fb1, self._fb2 = camera._get_temporary_fbs(2, 'f2')

        self._average = PostprocessPass(
            self.ctx,
            self.shadermgr,
            AVERAGE_PROG
        )
        self._fill = PostprocessPass(
            self.ctx,
            self.shadermgr,
            COPY_PROG
        )

    def enter(self, t, dt):
        self._fb1.use()
        self._fb1.clear()

    def exit(self, t, dt):
        self._fb2.use()
        self._fb2.clear()

        self.ctx.blend_func = moderngl.ONE, moderngl.ZERO

        # Fraction to reduce by each pass
        frac = 1 / self.pxsize

        # Pass 1: downsample by frac in the y direction
        self._average.set_region(1, frac)
        self._average.render(
            image=self._fb1,
            blur_direction=(0, 1),
            pxsize=self.pxsize,
            uvscale=(1, self.pxsize),
        )
        self._fb1.use()

        # Pass 2: downsample by frac in the x direction
        self._average.set_region(frac, frac)
        self._average.render(
            image=self._fb2,
            blur_direction=(1, 0),
            pxsize=self.pxsize,
            uvscale=(self.pxsize, 1)
        )

        # Pass 3: scale the downsampled image to the screen
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        fb1_tex = self._fb1.color_attachments[0]
        lin = fb1_tex.filter
        fb1_tex.filter = moderngl.NEAREST, moderngl.NEAREST
        self._outer_fb.use()
        self._fill.render(image=self._fb1, pxsize=self.pxsize)
        fb1_tex.filter = lin
