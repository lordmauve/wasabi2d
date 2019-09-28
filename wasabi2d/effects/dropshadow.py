"""A drop-shadow effect.

Very similar to the blur effect (wasabi2d.effects.blur) but composite
the original image on top.

"""
from typing import Tuple, List
from dataclasses import dataclass

import moderngl
import numpy as np

from .base import PostprocessPass
from .blur import Blur


def gaussian(x, mu, sig):
    """Calculate a gaussian function."""
    return np.exp(-np.power(x - mu, 2.) / (2 * np.power(sig, 2.)))


COMPOSITE_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;
uniform sampler2D blurred;
uniform float radius;
uniform vec2 offset;
uniform float opacity;

const vec3 BLACK = vec3(0, 0, 0);


void main()
{
    vec2 tex_offset = vec2(1.0, -1.0) * offset / textureSize(image, 0);

    vec4 image = texture(image, uv);

    float shadow_a = texture(blurred, uv - tex_offset).a * opacity;

    float alpha = image.a;
    float dest_alpha = alpha + (1 - alpha) * shadow_a;

    f_color = vec4(
        (image.rgb + (1 - alpha) * shadow_a * BLACK) / dest_alpha,
        dest_alpha
    );
}

"""


@dataclass
class Dropshadow:
    """A drop shadow effect."""
    ctx: moderngl.Context
    shadermgr: 'wasabi2d.layers.ShaderManager'
    radius: float = 10.0
    offset: Tuple[float, float] = (1.0, 1.0)
    opacity: float = 1.0

    camera: 'wasabi2d.scene.Camera' = None

    def _set_camera(self, camera: 'wasabi2d.scene.Camera'):
        """Resize the effect for this viewport."""
        self.camera = camera
        self._fb = camera._make_fb('f2')
        self.blur = Blur(
            self.ctx,
            self.shadermgr,
            self.radius
        )
        self.blur._set_camera(camera)
        self.blur._outer_fb = self._fb
        self._composite = PostprocessPass(
            self.ctx,
            self.shadermgr,
            COMPOSITE_PROG
        )

    def enter(self, t, dt):
        self.blur.radius = self.radius
        self.blur.enter(t, dt)

    def exit(self, t, dt):
        self._fb.clear()
        self.blur.exit(t, dt)
        self.ctx.screen.use()
        self._composite.render(
            blurred=self._fb,
            image=self.blur._fb1,
            offset=self.offset,
            opacity=self.opacity,
        )

