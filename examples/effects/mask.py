"""Example of using one layer to mask another."""
import wasabi2d as w2d

scene = w2d.Scene()
center = (scene.width / 2, scene.height / 2)

photo = scene.layers[0].add_sprite(
    'positano',
    pos=center
)
photo.scale = max(
    scene.width / photo.width,
    scene.height / photo.height
)

mask = scene.layers[1].add_circle(
    radius=100,
    pos=center,
)

scene.chain = [
    w2d.chain.Mask(
        w2d.chain.Layers([1]),
        w2d.chain.LayerRange(stop=0),
    )
]


@w2d.event
def on_mouse_move(pos):
    mask.pos = pos


@w2d.event
def on_mouse_down(pos):
    w2d.animate(mask, tween='decelerate', duration=0.2, scale=2)


@w2d.event
def on_mouse_up(pos):
    w2d.animate(mask, tween='bounce_end', duration=0.5, scale=1)


w2d.run()
