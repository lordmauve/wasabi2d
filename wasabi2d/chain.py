"""Classes for representing the render graph."""
from typing import Optional, List, Tuple
from dataclasses import dataclass
from functools import partial
import importlib
from collections import Counter
from contextlib import contextmanager

import numpy as np

from .color import convert_color


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


def to_node(val):
    """Convert a user-provided value to a ChainNode.

    This allows several shortcuts for specifying layers to a node.
    """
    if isinstance(val, ChainNode):
        return val

    if isinstance(val, int):
        return Layers([val])

    if isinstance(val, list):
        types = Counter(map(type, val))

        if len(types) == 1:
            typ, _ = types.popitem()
            if typ is int:
                return Layers(val)

        return Merge([to_node(v) for v in val])

    raise TypeError(f"Cannot convert {val!r} to ChainNode.")


@dataclass
class Merge(ChainNode):
    """Draw each of the given chain nodes in order."""
    nodes: List[ChainNode]

    def draw(self, scene):
        for node in self.nodes:
            node.draw(scene)


class Effect(ChainNode):
    """Apply a post-processing effect to the contained subchain."""
    __slots__ = (
        'draw', '_effect', '_subchain', '_camera', '_effect_keys',
    )

    def __init__(self, child_node: ChainNode, effect: str, params: dict):
        child_node = to_node(child_node)

        mod = importlib.import_module(f'wasabi2d.effects.{effect}')
        cls = getattr(mod, effect.title())
        self._effect_keys = set(cls.__dataclass_fields__)

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
    vec4 mask = texture(mask, uv);

    float a = %s;

    if (paint_frag.a * a < 1e-6) {
        discard;
    }
    f_color = vec4(paint_frag.rgb / paint_frag.a, paint_frag.a * a);
}
"""

MASK_FUNCS = {
    'inside': 'mask.a',
    'outside': '1 - mask.a',
    'luminance': 'dot(mask.rgb, vec3(0.3, 0.6, 0.1))',
}


@contextmanager
def rendered_node(scene, node):
    """Context manager to render a node to a temporary framebuffer.

    The framebuffer is reserved for the duration of the context, but then
    released.

    """
    camera = scene.camera
    with camera.temporary_fb() as fb:
        with camera.bind_framebuffer(fb):
            node.draw(scene)
        yield fb


@dataclass
class Mask(ChainNode):
    """Draw one 'paint' layer only where the 'mask' layer is opaque."""

    mask: ChainNode
    paint: ChainNode
    function: str = 'inside'

    def __post_init__(self):
        self.mask = to_node(self.mask)
        self.paint = to_node(self.paint)

    def draw(self, scene):
        """Draw the effect."""
        with rendered_node(scene, self.mask) as mask, \
                rendered_node(scene, self.paint) as paint:
            scene.camera.run_shader(
                MASK_PROG % MASK_FUNCS[self.function],
                paint=paint,
                mask=mask,
            )


class Fill(ChainNode):
    """Fill the screen with a single colour.

    This can be useful as input to another chain node, such as a mask. Note
    that ``Scene.background`` is also available if you simply want to clear
    the screen to a certain colour before rendering.

    """
    color: Tuple[float, float, float, float]

    def __init__(self, color):
        self.color = color

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, v):
        self._color = convert_color(v)

    def draw(self, scene):
        """Draw the effect."""
        scene.ctx.clear(*self._color)


DISPLACEMENT_PROG = """ \
#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D paint;
uniform sampler2D displacement;
uniform float scale;


void main()
{
    vec4 disp_frag = texture(displacement, uv);

    if (disp_frag.a < 1e-6) {
        discard;
    }
    vec3 unpremultiplied = disp_frag.rgb / disp_frag.a;
    float r = unpremultiplied.r;
    float g = unpremultiplied.g;
    float b = unpremultiplied.b;
    vec2 offset = (vec2(%s, %s) - vec2(0.5, 0.5)) * (2.0 * scale);

    vec4 paint_frag = texture(paint, uv + offset / textureSize(paint, 0));
    if (paint_frag.a < 1e-6) {
        discard;
    }
    f_color = vec4(paint_frag.rgb / paint_frag.a, paint_frag.a * disp_frag.a);
}
"""


@dataclass
class DisplacementMap(ChainNode):
    """Offset one input using the values of another."""

    paint: ChainNode
    displacement: ChainNode
    scale: float = 10.0
    x_channel: str = 'r'
    y_channel: str = 'g'

    def draw(self, scene):
        """Draw the effect."""
        with rendered_node(scene, self.displacement) as disp, \
                rendered_node(scene, self.paint) as paint:
            scene.camera.run_shader(
                DISPLACEMENT_PROG % (self.x_channel, self.y_channel),
                paint=paint,
                displacement=disp,
                scale=self.scale
            )
