"""Example of the punch effect."""
import math
from wasabi2d import run, Scene, event, keys


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


@event
def on_key_down(key, mod):
    if key == keys.F12:
        scene.screenshot()


run()
