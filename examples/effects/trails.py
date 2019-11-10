"""Example of the light bloom effect."""
from wasabi2d import run, Scene, event, Vector2
from wasabi2d.actor import Actor


scene = Scene()
scene.background = 'red'

logo = Actor(
    scene.layers[0].add_sprite(
        'wasabi2d',
        pos=(scene.width / 2, scene.height / 2),
    )
)
logo.v = Vector2(1, -1)
scene.layers[0].set_effect(
    'trails',
    fade=0.7
)


@event
def update(dt):
    logo.pos += logo.v
    if logo.top < 0 or logo.bottom >= scene.height:
        logo.v.y *= -1
    if logo.left < 0 or logo.right >= scene.width:
        logo.v.x *= -1


run()
