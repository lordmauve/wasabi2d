import math
import itertools
import numpy as np
import wasabi2d as w2d
from wasabi2d import Vector2, keys

INVISIBLE = (0, 0, 0, 0)
GREEN = (0.3, 1.3, 0.3)
LINE_W = 1
SHIP_PTS = [(10, 0), (-5, 5), (-3, 0), (-5, -5)]

GRAVITY = 0.5e7
ACCEL = 100
ROTATION_SPEED = 2


def forward(ship, length=1) -> Vector2:
    """Get a vector in the direction of the ship."""
    v = Vector2()
    v.from_polar((length, math.degrees(ship.angle)))
    return v


def make_player(pos, angle=0):
    ship = scene.layers[0].add_polygon(
        SHIP_PTS,
        fill=False,
        color=GREEN,
        stroke_width=LINE_W,
    )
    ship.pos = ship.initial_pos = pos
    ship.angle = ship.initial_angle = angle
    ship.v = forward(ship, 160)
    ship.initial_v = Vector2(ship.v)
    ship.radius = 7
    ship.dead = False
    return ship


scene = w2d.Scene()
scene.chain = [
    w2d.LayerRange()
    .wrap_effect('trails', alpha=0.6, fade=0.3)
    .wrap_effect('bloom', radius=3)
]

particles = scene.layers[0].add_particle_group(grow=0.1, max_age=0.3)
player1 = make_player(
    pos=(scene.width / 4, scene.height / 2),
    angle=-math.pi * 0.5
)
player2 = make_player(
    pos=(scene.width * 3 / 4, scene.height / 2),
    angle=math.pi * 0.5
)

star = scene.layers[0].add_circle(
    radius=40,
    fill=False,
    color=GREEN,
    stroke_width=LINE_W,
    pos=(scene.width / 2, scene.height / 2)
)

objects = [player1, player2]

controls = [
    (player1, keys.W, keys.A, keys.D, keys.E),
    (player2, keys.UP, keys.LEFT, keys.RIGHT, keys.RETURN),
]


def collides(a, b) -> bool:
    """Test if two objects have collided."""
    sep = a.pos - b.pos
    radii = a.radius + b.radius

    return Vector2(*sep).length_squared() < radii * radii


async def respawn(obj):
    obj.dead = True
    obj.color = INVISIBLE
    await w2d.clock.coro.sleep(3)
    objects.append(obj)
    obj.dead = False
    obj.angle = obj.initial_angle
    obj.v = Vector2(obj.initial_v)
    obj.pos = obj.initial_pos

    ring = scene.layers[0].add_circle(
        radius=40,
        pos=obj.pos,
        color=GREEN[:3] + (0,),
        fill=False,
        stroke_width=LINE_W,
    )
    w2d.tone.play(256, 1.0)
    await w2d.animate(
        ring,
        'accelerate',
        duration=0.5,
        scale=0.1,
        color=GREEN,
        stroke_width=10,
    )
    ring.delete()
    for i in range(11):
        obj.color = INVISIBLE if i % 2 else GREEN
        await w2d.clock.coro.sleep(0.1)


@w2d.event
def update(keyboard, dt):
    dt = min(dt, 0.5)
    dead = set()

    for o in objects:
        sep = Vector2(*star.pos - o.pos)
        dist = sep.magnitude()
        if dist > 1000:
            # If it's flying off into space, kill it
            dead.add(o)
            o.silent = True
        o_u = o.v
        o.v += GRAVITY / (dist * dist) * sep.normalize() * dt
        o.pos += (o_u + o.v) * 0.5 * dt

    for o in objects:
        if collides(o, star):
            dead.add(o)
    objects[:] = [o for o in objects if o not in dead]

    for a, b in itertools.combinations(objects, 2):
        if collides(a, b):
            dead |= {a, b}
    objects[:] = [o for o in objects if o not in dead]

    for o in dead:
        particles.emit(
            o.radius ** 2,
            size=1,
            pos=o.pos,
            pos_spread=o.radius * 0.7,
            vel=o.v * 0.2,
            vel_spread=50,
            color=GREEN
        )

    for obj, up, left, right, _ in controls:
        if obj in dead:
            dead.discard(obj)
            w2d.tone.play(20, 1.0, waveform='square')
            w2d.clock.coro.run(respawn(obj))
            continue
        elif obj.dead:
            continue

        if keyboard[up]:
            obj.v += forward(obj, ACCEL * dt)
            particles.emit(
                np.random.poisson(30 * dt),
                size=2,
                pos=obj.pos + forward(obj, -7),
                vel=obj.v + forward(obj, -100),
                vel_spread=4,
                color=GREEN
            )

        if keyboard[left]:
            obj.angle -= ROTATION_SPEED * dt
        elif keyboard[right]:
            obj.angle += ROTATION_SPEED * dt

    for o in dead:
        if not getattr(o, 'silent', False):
            w2d.tone.play(30, 0.3, waveform='square')
        o.delete()


@w2d.event
def on_key_down(key):
    for ship, _, _, _, shoot_button in controls:
        if shoot_button is key:
            break
    else:
        return

    if ship.dead:
        return

    bullet = scene.layers[0].add_rect(
        4, 4,
        pos=ship.pos + forward(ship, 12),
        color=GREEN
    )
    bullet.radius = 2.8
    bullet.v = ship.v + forward(ship, 200)
    objects.append(bullet)
    waveform = 'triangle' if ship is player1 else 'saw'
    w2d.tone.play(200, 0.3, waveform=waveform, volume=0.6)


w2d.run()
