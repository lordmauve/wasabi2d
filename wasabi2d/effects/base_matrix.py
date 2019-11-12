"""Base class for effects that simply apply a color matrix."""
from dataclasses import dataclass
import abc

import moderngl
import numpy as np

from ..shaders import bind_framebuffer
from .base import PostprocessPass


COLOR_MATRIX_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D image;
uniform mat4 color_matrix;

const vec3 GAMMA = vec3(2.2, 2.2, 2.2);
const vec3 INV_GAMMA = 1.0 / GAMMA;

vec3 srgb_to_linear(vec3 rgb) {
    return pow(rgb, GAMMA);
}

vec3 linear_to_srgb(vec3 lrgb) {
    return pow(lrgb, INV_GAMMA);
}

void main()
{
    vec4 frag = texture(image, uv);
    if (frag.a < 1e-6) {
        discard;
    }
    vec3 rgb = frag.rgb;
    if (frag.a > 1e-6) {
        rgb /= frag.a;
    }
    vec4 converted = vec4(srgb_to_linear(rgb), frag.a) * color_matrix;
    f_color = vec4(linear_to_srgb(converted.rgb), converted.a);
}
"""


@dataclass
class BaseMatrix(metaclass=abc.ABCMeta):
    ctx: moderngl.Context

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera

        self._color_mat = PostprocessPass(
            self.ctx,
            COLOR_MATRIX_PROG
        )

    @abc.abstractmethod
    def get_matrix(self) -> np.ndarray:
        """Get the matrix to draw.

        The matrix should be (4x4).
        """

    def draw(self, draw_layer):
        """Subclasses should implement this to pass the matrix to draw."""
        with self.camera.temporary_fb() as fb:
            with bind_framebuffer(self.ctx, fb, clear=True):
                draw_layer()

            self._color_mat.render(
                image=fb,
                color_matrix=tuple(self.get_matrix().reshape(-1)),
            )
