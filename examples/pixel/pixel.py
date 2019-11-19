"""Example of using one layer to mask another."""
import wasabi2d as w2d

scene = w2d.Scene(width=320, height=200)

mask = scene.layers[1].add_circle(
    radius=10,
    pos=(160, 100),
)


@w2d.event
def on_mouse_move(pos):
    mask.pos = pos


w2d.run()
