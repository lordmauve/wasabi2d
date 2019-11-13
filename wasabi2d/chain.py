"""Classes for representing the render graph."""
from typing import Optional, List
from dataclasses import dataclass
from functools import partial
import importlib

import numpy as np


class ChainNode:
    """Mix-in class for chain nodes to wrap them in an additional effect."""

    def wrap_effect(self, name: str, **parameters) -> 'Effect':
        """Wrap this layer range in an effect.

        The name and parameters are identical to ``Layer.set_effect()``.

        This is a shortcut for constructing the effect object directly.

        :param name: The name of an effect to enable.
        :param parameters: Parameters to control the effect.
        :return: An Effect object, which can be used to change parameters for
                 the effect, or to wrap this effect in another effect.

        """
        return Effect(self, name, parameters)


@dataclass
class LayerRange(ChainNode):
    """Render a range of layers, in order of lowest id to highest id.

    Only existing layers are rendered; any that do not are skipped - but will
    be rendered as soon as they are created.

    Unlike range(), start and stop are *inclusive*.
    """
    start: Optional[int] = None
    stop: Optional[int] = None

    def draw(self, scene):
        """Draw the selected layers."""
        layers = scene.layers

        start = self.start if self.start is not None else -np.inf
        stop = self.stop if self.stop is not None else np.inf

        for k in sorted(layers):
            if start <= k <= stop:
                layers[k]._draw()


@dataclass
class Layers(ChainNode):
    """Render specific layers in the specified order.

    Only existing layers are rendered; any that do not are skipped - but will
    be rendered as soon as they are created.

    """
    layers: List[int]

    def draw(self, scene):
        for layer_num in self.layers:
            if layer_num in scene.layers:
                scene.layers[layer_num]._draw()


class Effect(ChainNode):
    """Apply a post-processing effect to the contained subchain."""
    __slots__ = (
        'draw', '_effect', '_subchain', '_camera', '_effect_keys',
    )

    def __init__(self, child_node: ChainNode, effect: str, params: dict):
        mod = importlib.import_module(f'wasabi2d.effects.{effect}')
        cls = getattr(mod, effect.title())
        self._effect_keys = set(effect.__dataclass_fields__)

        unexpected = params.keys() - self._effect_keys
        if unexpected:
            raise TypeError(
                f"{effect} does not accept attributes {unexpected}"
            )

        self._effect = None
        self._subchain = child_node
        self._camera = None

        def draw(scene):
            """Bind the context and instantiate the effect."""
            ctx = scene.ctx
            self._effect = cls(ctx, **params)
            self.draw = self.real_draw
            self.draw(scene)
        self.draw = draw

    def real_draw(self, scene):
        if scene.camera is not self._camera:
            self._camera = scene.camera
            self._effect._set_camera(self._camera)
        self._effect.draw(partial(self._subchain.draw, scene))

    def __getattr__(self, k):
        if k in self._effect_keys:
            return getattr(self._effect, k)
        return object.__getattr__(self, k)

    def __setattr__(self, k, v):
        if not k.startswith('_') and k in self._effect_keys:
            setattr(self._effect, k, v)
        object.__setattr__(self, k, v)


MASK_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D paint;
uniform sampler2D mask;

void main()
{
    vec4 paint_frag = texture(paint, uv);
    float mask_a = texture(mask, uv).a;

    if (paint_frag.a * mask_a < 1e-6) {
        discard;
    }
    f_color = vec4(paint_frag.rgb / paint_frag.a, paint_frag.a * mask_a);
}
"""


@dataclass
class Mask(ChainNode):
    """Draw one 'paint' layer only where the 'mask' layer is opaque."""

    mask: ChainNode
    paint: ChainNode

    def draw(self, scene):
        """Draw the effect."""
        camera = scene.camera
        with camera.temporary_fb() as mask_fb:
            with camera.bind_framebuffer(mask_fb):
                self.mask.draw(scene)

            with camera.temporary_fb() as paint_fb, \
                    camera.bind_framebuffer(paint_fb):
                self.paint.draw(scene)

            camera.run_shader(
                MASK_PROG,
                paint=paint_fb,
                mask=mask_fb,
            )
