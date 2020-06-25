import math
import numpy as np
import wasabi2d as w2d
from wasabi2d import Vector2, keys
from wasabi2d.keyboard import keyboard
from pygame import joystick

INVISIBLE = (0, 0, 0, 0)
GREEN = (0.3, 1.3, 0.3)
TRANSPARENT_GREEN = (*GREEN[:3], 0)
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

mode_720p = 1280, 720
mode_1080p = 1920, 1080
scene = w2d.Scene(*mode_720p, fullscreen=True)
scene.chain = [
    w2d.LayerRange()
    .wrap_effect('trails', alpha=0.4, fade=0.08)
    .wrap_effect('bloom', radius=8)
]

center = Vector2(scene.width, scene.height) * 0.5

score1 = scene.layers[0].add_label('0', pos=(10, 40), fontsize=30, color=GREEN)
score2 = scene.layers[0].add_label(
    '0',
    pos=(scene.width - 10, 40),
    align='right',
    fontsize=30,
    color=GREEN
)
score1.value = score2.value = 0

fps = scene.layers[0].add_label(
    'FPS: 60',
    pos=(10, scene.height - 10),
    fontsize=20,
    color=GREEN,
)

particles = scene.layers[0].add_particle_group(grow=0.1, max_age=2)
particles.add_color_stop(0, GREEN)
particles.add_color_stop(2, TRANSPARENT_GREEN)

player1 = make_player(
    pos=center - Vector2(200, 0),
    angle=-math.pi * 0.5
)
player1.score_label = score2
player2 = make_player(
    pos=center + Vector2(200, 0),
    angle=math.pi * 0.5
)
player2.score_label = score1

star = scene.layers[-1].add_circle(
    radius=40,
    fill=False,
    color=GREEN,
    stroke_width=LINE_W,
    pos=(scene.width / 2, scene.height / 2)
)

objects = [star, player1, player2]

joystick.init()
sticks = [joystick.Joystick(i) for i in range(min(joystick.get_count(), 2))]
for s in sticks:
    s.init()


def pressed(key):
    return lambda: keyboard[key]


controls = [
    (player1, pressed(keys.W), pressed(keys.A), pressed(keys.D), keys.E),
    (player2, pressed(keys.UP), pressed(keys.LEFT), pressed(keys.RIGHT), keys.RETURN),
]

def make_stick_controls(s):
    return (
        lambda: s.get_axis(1) < -0.5,
        lambda: s.get_axis(0) < -0.5,
        lambda: s.get_axis(0) > 0.5,
    )

for i, s in enumerate(sticks):
    player, *_, shoot = controls[i]
    controls[i] = (
        player,
        *make_stick_controls(s),
        shoot,
    )


def collides(a, b) -> bool:
    """Test if two objects have collided."""
    sep = a.pos - b.pos
    radii = a.radius + b.radius

    return Vector2(*sep).length_squared() < radii * radii


async def respawn(obj):
    obj.score_label.value += 1
    obj.score_label.text = str(obj.score_label.value)

    obj.dead = True
    obj.color = INVISIBLE
    await w2d.clock.coro.sleep(3)

    ring = scene.layers[0].add_circle(
        radius=40,
        pos=obj.initial_pos,
        color=TRANSPARENT_GREEN,
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

    objects.append(obj)
    obj.dead = False
    obj.angle = obj.initial_angle
    obj.pos = obj.initial_pos
    obj.v = Vector2(obj.initial_v)
    for i in range(11):
        obj.color = INVISIBLE if i % 2 else GREEN
        await w2d.clock.coro.sleep(0.1)
        if obj.dead:
            return


def collision_pairs(objects):
    objects.sort(key=lambda o: o.pos[0] - o.radius)

    open = []
    for o in objects:
        x = o.pos[0]
        r = o.radius
        left = x - r
        new_open = []
        for o2r, o2 in open:
            if o2r < left:
                continue
            new_open.append((o2r, o2))
            if collides(o, o2):
                yield o, o2
        right = x + r
        open.append((right, o))


def update(dt):
    fps.text = f'FPS: {scene.fps:0.1f}'
    dt = min(dt, 0.5)
    dead = set()

    for o in objects:
        if o is star:
            continue

        sep = Vector2(*star.pos - o.pos)
        dist = sep.magnitude()
        if dist > 1500:
            # If it's flying off into space, kill it
            dead.add(o)
            o.silent = True
        o_u = o.v
        o.v += GRAVITY / (dist * dist) * sep.normalize() * dt
        o.pos += (o_u + o.v) * 0.5 * dt

    for a, b in collision_pairs(objects):
        dead |= {a, b}
    dead.discard(star)
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

        if up():
            obj.v += forward(obj, ACCEL * dt)
            particles.emit(
                np.random.poisson(30 * dt),
                size=2,
                pos=obj.pos + forward(obj, -7),
                vel=obj.v + forward(obj, -100),
                vel_spread=4,
                color=GREEN
            )

        if left():
            obj.angle -= ROTATION_SPEED * dt
        elif right():
            obj.angle += ROTATION_SPEED * dt

    for o in dead:
        if not getattr(o, 'silent', False):
            w2d.tone.play(30, 0.3, waveform='square')
        o.delete()


@w2d.event
def on_key_down(key):
    if key == keys.ESCAPE:
        score1.text = score2.text = '0'
        score1.value = score2.value = 0
    elif key == keys.P:
        w2d.clock.default_clock.paused = not w2d.clock.default_clock.paused
        return

    for ship, _, _, _, shoot_button in controls:
        if shoot_button is key:
            break
    else:
        return
    shoot(ship)


def shoot(ship):
    if ship.dead:
        return

    bullet = scene.layers[0].add_rect(
        4, 4,
        pos=ship.pos + forward(ship, 12),
        color=GREEN
    )
    bullet.radius = 2.8

    v = forward(ship, 200)
    bullet.v = ship.v + v
    # Recoil!
    #ship.v -= v * 0.02

    objects.append(bullet)
    waveform = 'triangle' if ship is player1 else 'saw'
    w2d.tone.play(200, 0.3, waveform=waveform, volume=0.6)


@w2d.event
def on_joybutton_down(joy, button):
    if joy >= 2:
        return
    ship = controls[joy][0]
    shoot(ship)

w2d.clock.each_tick(update, strong=True)
w2d.run()
