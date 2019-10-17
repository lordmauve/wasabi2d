"""Example of the punch effect."""
import math
from wasabi2d import run, Scene, event


scene = Scene()

logo1 = scene.layers[0].add_sprite(
    'wasabi2d',
    pos=(scene.width / 4, scene.height / 2),
    scale=0.5
)
effect1 = scene.layers[0].set_effect(
    'pixellate',
    pxsize=10
)

logo2 = scene.layers[1].add_sprite(
    'wasabi2d',
    pos=(scene.width * 3 / 4, scene.height / 2),
    scale=0.5
)
effect2 = scene.layers[1].set_effect(
    'pixellate',
    pxsize=10,
    antialias=0.0
)

scene.layers[2].add_label(
    f'antialias={effect1.antialias}',
    pos=(scene.width / 4, scene.height - 20),
    align='center',
)
scene.layers[2].add_label(
    f'antialias={effect2.antialias}',
    pos=(scene.width * 3 / 4, scene.height - 20),
    align='center',
)


@event
def update(dt, t):
    logo1.angle += 0.5 * dt
    logo2.angle += 0.5 * dt


run()
