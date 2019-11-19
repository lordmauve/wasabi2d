"""Example of using one layer to mask another."""
import wasabi2d as w2d

TILE = 21

scene = w2d.Scene(width=TILE * 15, height=TILE * 10, scaler=True)
scene.background = '#5e81a2'
scene.layers[1].set_effect('dropshadow', radius=2, offset=(0, 1))

alien = scene.layers[1].add_sprite(
    'pc_standing',
    anchor_x=10,
    anchor_y=21,
    pos=(210, TILE * 9),
)


def create_platform(x1, x2, y):
    length = x2 - x1
    if length == 1:
        scene.layers[1].add_sprite(
            'platform_single',
            pos=(x1 * TILE, y * TILE),
            anchor_x=0,
            anchor_y=0,
        )
        return
    for i in range(length):
        if i == 0:
            sprite = 'platform_l'
        elif i == (length - 1):
            sprite = 'platform_r'
        else:
            sprite = 'platform_m'

        scene.layers[1].add_sprite(
            sprite,
            pos=((x1 + i) * TILE, (y * TILE)),
            anchor_x=0,
            anchor_y=0,
        )

create_platform(0, 15, 9)
create_platform(3, 6, 6)


w2d.run()
