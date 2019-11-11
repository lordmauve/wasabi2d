"""Convert colours to sepia."""
from dataclasses import dataclass

import moderngl
import numpy as np

from ..shaders import bind_framebuffer, blend_func
from .base import PostprocessPass


SEPIA_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D image;
uniform mat3 color_matrix;

void main()
{
    vec4 frag = texture(image, uv);
    if (frag.a < 1e-6) {
        discard;
    }
    f_color = vec4((frag.rgb / frag.a) * color_matrix, frag.a);
}
"""

SRC_ARR = np.array([
    [0.393, 0.769, 0.189],
    [0.349, 0.686, 0.168],
    [0.272, 0.534, 0.131],
])

DEST_ARR = np.array([
    [0.607, -0.769, -0.189],
    [-0.349, 0.314, -0.168],
    [-0.272, -0.534, 0.869],
])


@dataclass
class Sepia:
    """A sepia effect."""

    ctx: moderngl.Context
    amount: float = 1.0

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera

        self._color_mat = PostprocessPass(
            self.ctx,
            SEPIA_PROG
        )

    def draw(self, draw_layer):
        matrix = SRC_ARR + (1 - self.amount) * DEST_ARR
        with self.camera.temporary_fb() as fb:
            with bind_framebuffer(self.ctx, fb, clear=True):
                draw_layer()

            self._color_mat.render(
                image=fb,
                color_matrix=tuple(matrix.reshape((-1))),
            )
