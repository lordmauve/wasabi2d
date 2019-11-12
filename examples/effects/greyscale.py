"""Example of the greyscale effect."""
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
grey = scene.layers[0].set_effect('greyscale')


@w2d.event
def on_mouse_move(pos):
    x, y = pos
    frac = x / scene.width
    grey.amount = frac


w2d.run()
