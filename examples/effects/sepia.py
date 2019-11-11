"""Example of the sepia effect."""
import wasabi2d as w2d

scene = w2d.Scene()

photo = scene.layers[0].add_sprite(
    'positano',
    pos=(scene.width / 2, scene.height / 2),
)
photo.scale = max(
    scene.width / photo.width,
    scene.height / photo.height
)
sepia = scene.layers[0].set_effect('sepia')


@w2d.event
def on_mouse_move(pos):
    x, y = pos
    frac = x / scene.width
    sepia.amount = frac


w2d.run()
