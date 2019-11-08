"""Classes for representing the render graph."""
from typing import Optional, Any
from dataclasses import dataclass
from functools import partial
import importlib


class ChainNode:
    """Mix-in class for chain nodes to wrap them in an additional effect."""

    def wrap_effect(self, name: str, **kwargs) -> Any:
        """Wrap this layer range in an effect.

        Return the effect object, which can be used to change parameters for
        the effect.

        """
        mod = importlib.import_module(f'wasabi2d.effects.{name}')
        cls = getattr(mod, name.title())
        return Effect(cls, kwargs, self)


@dataclass
class LayerRange(ChainNode):
    """Render a range of layers."""
    start: Optional[int] = None
    stop: Optional[int] = None

    def draw(self, scene):
        """Draw the selected layers."""
        layers = scene.layers
        if self.start is None and self.stop is None:
            layer_test = lambda k: True  # noqa: E731: cmon now
        else:
            layer_test = range(self.start, self.stop).__contains__
        for k in sorted(layers):
            if layer_test:
                layers[k]._draw()


class Effect(ChainNode):
    """Apply a post-processing effect to the contained subchain."""
    __slots__ = (
        'draw', '_effect', '_subchain', '_camera', '_effect_keys',
    )

    def __init__(self, effect, params, subchain):
        self._effect_keys = set(effect.__dataclass_fields__)

        unexpected = params.keys() - self._effect_keys
        if unexpected:
            raise TypeError(
                f"{effect} does not accept attributes {unexpected}"
            )

        self._effect = None
        self._subchain = subchain
        self._camera = None

        def draw(scene):
            """Bind the context and instantiate the effect."""
            ctx = scene.ctx
            self._effect = effect(ctx, **params)
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
