"""Pixellate by averaging pixel values."""
from dataclasses import dataclass

import moderngl

from ..shaders import bind_framebuffer, blend_func
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
    pxsize: int = 10
    antialias: float = 1.0

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera

        self._average = PostprocessPass(
            self.ctx,
            AVERAGE_PROG
        )
        self._fill = PostprocessPass(
            self.ctx,
            COPY_PROG
        )

    def draw(self, draw_layer):
        # Fraction to reduce by each pass
        frac = 1 / self.pxsize

        # By turning off the averaging we can remove the antialiasing
        epxsize = round((self.pxsize - 1) * self.antialias) + 1

        with self.camera.temporary_fbs(2, 'f2') as (fb1, fb2):
            with bind_framebuffer(self.ctx, fb1, clear=True):
                draw_layer()

                with blend_func(self.ctx, moderngl.ONE, moderngl.ZERO):
                    with bind_framebuffer(self.ctx, fb2, clear=True):
                        # Pass 1: downsample by frac in the y direction
                        self._average.set_region(1, frac)
                        self._average.render(
                            image=fb1,
                            blur_direction=(0, 1),
                            pxsize=epxsize,
                            uvscale=(1, self.pxsize),
                        )

                    # Pass 2: downsample by frac in the x direction
                    self._average.set_region(frac, frac)
                    self._average.render(
                        image=fb2,
                        blur_direction=(1, 0),
                        pxsize=epxsize,
                        uvscale=(self.pxsize, 1)
                    )

            # Pass 3: scale the downsampled image to the screen
            fb1_tex = fb1.color_attachments[0]
            lin = fb1_tex.filter
            fb1_tex.filter = moderngl.NEAREST, moderngl.NEAREST
            self._fill.render(image=fb1, pxsize=self.pxsize)
            fb1_tex.filter = lin
