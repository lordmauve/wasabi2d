import math
import wasabi2d as w2d
from wasabi2d import Vector2


scene = w2d.Scene()
scene.background = (0, 0.03, 0.1)

ship = scene.layers[2].add_sprite(
    'ship',
    pos=(scene.width / 2, scene.height / 2),
    anchor_x=0
)
circ = scene.layers[0].add_circle(
    radius=30,
    pos=(100, 100),
    color='cyan',
    fill=False,
    stroke_width=3.0,
)
star = scene.layers[0].add_star(
    points=6,
    inner_radius=30,
    outer_radius=60,
    pos=(400, 100),
    color='yellow'
)
scene.layers[0].add_circle(
    radius=60,
    pos=(480, 120),
    color='#ff000088',
)
lbl = scene.layers[0].add_label(
    "Time: 0s",
    font='bubblegum_sans',
    pos=(scene.width * 0.5, 560),
    align='right'
)
lbl.color = 'yellow'

r = scene.layers[0].add_rect(
    width=400,
    height=50,
    pos=(480, 500),
    fill=True,
    color='#ff00ff88',
)

poly = scene.layers[0].add_polygon(
    [
        (-20, 20),
        (5, 60),
        (50, 50),
        (50, -60),
        (-10, -80),
        (-50, -50),
        (0, -30),
    ],
    pos=(700, 300),
    color='#888888ff',
    fill=False,
)
poly.stroke_width = 0


scene.layers[1].set_effect(
    'bloom',
    threshold=0.9,
    radius=50
)
particles = scene.layers[1].add_particle_group(
    texture='smoke',
    grow=3,
    max_age=2,
    gravity=(0, -100),
    drag=0.5,
)
particles.add_color_stop(0, (2, 2, 2, 1))
particles.add_color_stop(0.3, (2.2, 0.8, 0, 1))
particles.add_color_stop(0, (1, 0, 0, 1))
particles.add_color_stop(1.0, 'gray')
particles.add_color_stop(2, (0.3, 0.3, 0.3, 0))


ship.vel = Vector2()


bullets = []


SHIFT = w2d.keymods.LSHIFT | w2d.keymods.RSHIFT


@w2d.event
def on_key_down(key, mod):
    if key == key.F11:
        import pdb
        pdb.set_trace()

    elif key == key.K_1:
        lbl.align = 'left'
    elif key == key.K_2:
        lbl.align = 'center'
    elif key == key.K_3:
        lbl.align = 'right'

    elif key == key.SPACE:
        bullet = scene.layers[0].add_sprite(
            'tiny_bullet',
            pos=ship.pos
        )
        bullet.color = (1, 0, 0, 1)
        bullet.vel = Vector2(600, 0).rotate_rad(ship.angle)
        bullet.power = 1.0
        bullets.append(bullet)
        w2d.sounds.laser.play()


def update_circ():
    circ.radius += 1
    poly.stroke_width += 0.01
    x, y = r.pos
    r.pos = (x, y - 1)


def rotate_star():
    """Animate the rotation of the star."""
    w2d.animate(
        star,
        'bounce_end',
        duration=1.0,
        angle=star.angle + math.pi / 3,
    )


rotate_star()

w2d.clock.schedule_interval(update_circ, 0.1)
w2d.clock.schedule_interval(rotate_star, 2.0)


@w2d.event
def update(t, dt, keyboard):
    ship.vel *= 0.3 ** dt

    speed = ship.vel.magnitude()
    lbl.text = f"Speed: {speed / 10:0.1f}m/s"
    lbl.scale = (speed / 100) ** 2 + 1

    accel = 300 * dt
    thrust = False
    if keyboard.right:
        thrust = True
        ship.vel[0] += accel
    elif keyboard.left:
        thrust = True
        ship.vel[0] -= accel
    if keyboard.up:
        thrust = True
        ship.vel[1] -= accel
    elif keyboard.down:
        thrust = True
        ship.vel[1] += accel

    ship.pos += ship.vel * dt

    if not (-1e-6 < ship.vel.magnitude_squared() < 1e-6):
        vx, vy = ship.vel
        ship.angle = math.atan2(vy, vx)

    if thrust:
        particles.emit(
            dt * 200,
            vel=-200 * ship.vel.normalize(),
            vel_spread=20,
            pos=ship.pos,
            size=8,
            spin_spread=3,
        )

    for b in bullets.copy():
        b.pos += b.vel * dt
        b.power = max(0, b.power - dt)
        b.angle += 3 * dt
        b.scale = 1 / (b.power + 1e-6)
        b.color = (1, 0, 0, b.power ** 0.5)
        if b.power < 0.01:
            b.delete()
            bullets.remove(b)


w2d.run()
