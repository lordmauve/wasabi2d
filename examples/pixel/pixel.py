"""Example of using one layer to mask another."""
import wasabi2d as w2d
import math
from pygame import Rect
from wasabi2d import Vector2
from wasabi2d.actor import Actor

TILE = 21
TILES_W = 15
TILES_H = 10

grid = set()
grid.update((x, TILES_H) for x in range(TILES_W))
grid.update((-1, y) for y in range(-TILES_H, TILES_H))
grid.update((TILES_W, y) for y in range(-TILES_H, TILES_H))

scene = w2d.Scene(
    width=TILE * TILES_W,
    height=TILE * TILES_H,
    scaler=True,
    pixel_art=True,
)
scene.background = '#5e81a2'
scene.layers[1].set_effect('dropshadow', radius=2, offset=(0, 1))

alien = scene.layers[1].add_sprite(
    'pc_standing',
    anchor_x=10,
    anchor_y=21,
    pos=(210, TILE * 9)
)
alien.fpos = Vector2(*alien.pos)
alien.v = Vector2(0, 0)
alien.stood = True
alien.crouch = False


def create_platform(x1, x2, y):
    length = x2 - x1
    if length == 1:
        grid.add((x1, y))
        scene.layers[1].add_sprite(
            'platform_single',
            pos=(x1 * TILE, y * TILE),
            anchor_x=0,
            anchor_y=0,
        )
        return
    for i in range(length):
        pos = x1 + i, y
        grid.add(pos)
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
create_platform(12, 14, 8)
create_platform(3, 6, 6)

ACCEL = 0.7
JUMP = 7.7
GRAVITY = 0.5
DRAG = 0.8


def world_to_grid(pos):
    x, y = pos
    return x / TILE, y / TILE


def collide_point(*pos):
    """Is the given world coordinate in the grid."""
    pos = {(x // TILE, y // TILE) for x, y in pos}
    return bool(pos & grid)


def tile_floor(val):
    return math.floor(val / TILE) * TILE


def tile_ceil(val):
    return math.ceil(val / TILE) * TILE


eps = 1e-4
BOUNDS = [
    Vector2(11 - eps, -eps),  # br
    Vector2(-10 + eps, -eps),  # bl
    Vector2(-10 + eps, -21 + eps),  # tl
    Vector2(11 - eps, -21 + eps),  # tr
]


def bounds():
    """Get the alien's bounds as a tuple (br, bl, tl, tr)."""
    pos = alien.fpos
    return tuple(pos + v for v in BOUNDS)


@w2d.event
def update(keyboard):
    x, y = alien.fpos
    vx, vy = alien.v

    y += vy
    alien.fpos.y = y

    eps = 1e-4

    br, bl, tl, tr = bounds()

    if alien.stood:
        belowl = bl + Vector2(0, 1)
        belowr = br + Vector2(0, 1)
        if not (collide_point(belowl, belowr)):
            alien.stood = False
            alien.image = 'pc_standing'
            vy += GRAVITY
    else:
        if vy + eps > y - tile_floor(y) > 0:
            if collide_point(bl, br):
                alien.image = 'pc_standing'
                alien.stood = True
                vy = 0
                y = tile_floor(y)
            else:
                alien.image = 'pc_falling'
        elif vy - eps < tl.y - tile_ceil(tl.y) < 0:
            if collide_point(tl, tr):
                print("oof")
                vy = 0
                y = tile_ceil(y)
        if not alien.stood:
            vy += GRAVITY

    if not alien.crouch:
        if keyboard.left:
            vx -= ACCEL
        elif keyboard.right:
            vx += ACCEL
    vx *= DRAG
    x += vx
    alien.fpos.x = x

    br, bl, tl, tr = bounds()

    if vx + eps > tr.x - tile_floor(tr.x) > 0:
        alien.scale_x = 1
        if collide_point(tr, br):
            vx = 0
            x = tile_floor(tr.x) - 11
    elif vx - eps < tl.x - tile_ceil(tl.x) < 0:
        alien.scale_x = -1
        if collide_point(tl, bl):
            vx = 0
            x = tile_ceil(tl.x) + 10
    alien.fpos.x = vx

    alien.v = Vector2(vx, vy)
    alien.pos = alien.fpos = Vector2(x, y)



@w2d.event
def on_key_down(key):
    if key is w2d.keys.UP:
        if alien.stood and not alien.crouch:
            alien.v.y = -JUMP
            alien.stood = False
            alien.image = 'pc_jumping'
    elif key is w2d.keys.DOWN:
        if alien.stood:
            print("crouch")
            alien.image = 'pc_crouch'
            alien.crouch = True


@w2d.event
def on_key_up(key):
    if key is w2d.keys.DOWN:
        if alien.crouch:
            alien.image = 'pc_standing'
            alien.crouch = False

w2d.run()
