"""Example of the punch effect."""
import math
from wasabi2d import run, Scene, event


scene = Scene()

logo = scene.layers[0].add_sprite(
    'wasabi2d',
    pos=(scene.width / 2, scene.height / 2),
)
effect = scene.layers[0].set_effect(
    'blur',
    radius=10
)


@event
def update(t):
    effect.radius = 20 * math.sin(t) ** 2


run()
