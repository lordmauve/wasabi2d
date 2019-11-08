"""Classes for representing the render graph."""
from typing import Optional
from dataclasses import dataclass


@dataclass
class LayerRange:
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
