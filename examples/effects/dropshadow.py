"""Example of the punch effect."""
import math
from wasabi2d import run, Scene, event, keys


scene = Scene()
scene.background = (1, 1, 1)

logo = scene.layers[0].add_sprite(
    'wasabi2d',
    pos=(scene.width / 2, scene.height / 2),
)
effect = scene.layers[0].set_effect(
    'dropshadow',
    radius=10,
    opacity=0.5
)


@event
def update(t):
    phase = math.sin(t) ** 2
    effect.radius = 20 * phase
    effect.offset = (20 * phase + 2,) * 2


@event
def on_key_down(key, mod):
    if key == keys.F12:
        scene.screenshot()


run()
