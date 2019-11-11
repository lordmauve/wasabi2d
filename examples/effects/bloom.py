"""Example of the light bloom effect."""
from wasabi2d import run, Scene


scene = Scene()

logo = scene.layers[0].add_sprite(
    'wasabi2d',
    pos=(scene.width / 2, scene.height / 2),
)
logo.color = (1.3, 1.3, 1.3, 1)
scene.layers[0].set_effect('bloom', radius=20, intensity=0.25)

run()
