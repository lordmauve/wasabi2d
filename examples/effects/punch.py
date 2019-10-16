"""Example of the punch effect."""
import math
from wasabi2d import run, Scene, event


scene = Scene()

logo = scene.layers[0].add_sprite(
    'wasabi2d',
    pos=(scene.width / 2, scene.height / 2),
)
effect = scene.layers[0].set_effect(
    'punch',
    factor=2.0
)


@event
def update(t):
    effect.factor = 0.5 + math.sin(t) ** 2


run()
