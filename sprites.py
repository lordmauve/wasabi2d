import math
from wasabi2d import event, run, sounds, Scene, Vector2, clock, animate


scene = Scene(antialias=8)
scene.background = (0, 0.02, 0.1)

ship = scene.layers[0].add_sprite(
    'ship',
    pos=(scene.width / 2, scene.height / 2)
)
circ = scene.layers[0].add_circle(
    radius=30,
    pos=(100, 100),
    color='cyan',
    fill=False
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
    "Hello y World!",
    font='bubblegum_sans',
    pos=(40, 560),
)
lbl.scale = 3
lbl.color = 'yellow'
r = scene.layers[0].add_rect(
    pos=(140, 560),
    width=200,
    height=2,
    color='yellow',
)


r = scene.layers[0].add_rect(
    width=400,
    height=50,
    pos=(480, 500),
    fill=True,
    color='#ff00ff88',
)

scene.layers[0].add_polygon(
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


ship.vel = Vector2()


bullets = []


@event
def on_key_down(key):
    if key == key.F12:
        scene.screenshot()

    elif key == key.SPACE:
        bullet = scene.layers[0].add_sprite(
            'tiny_bullet',
            pos=ship.pos
        )
        bullet.color = (1, 0, 0, 1)
        bullet.vel = Vector2(600, 0).rotate_rad(ship.angle)
        bullet.power = 1.0
        bullets.append(bullet)
        sounds.laser.play()


def update_circ():
    circ.scale += 0.01
    x, y = r.pos
    r.pos = (x, y - 1)


clock.schedule_interval(update_circ, 0.1)


def rotate_star():
    """Animate the rotation of the star."""
    animate(
        star,
        'bounce_end',
        duration=1.0,
        angle=star.angle + math.pi / 3,
    )


rotate_star()
clock.schedule_interval(rotate_star, 2.0)


@event
def update(dt, keyboard):
    ship.vel *= 0.3 ** dt

    accel = 300 * dt
    if keyboard.right:
        ship.vel[0] += accel
    elif keyboard.left:
        ship.vel[0] -= accel
    if keyboard.up:
        ship.vel[1] -= accel
    elif keyboard.down:
        ship.vel[1] += accel

    ship.pos += ship.vel * dt

    if not (-1e-6 < ship.vel.magnitude_squared() < 1e-6):
        vx, vy = ship.vel
        ship.angle = math.atan2(vy, vx)

    for b in bullets.copy():
        b.pos += b.vel * dt
        b.power = max(0, b.power - dt)
        b.angle += 3 * dt
        b.scale = 1 / (b.power + 1e-6)
        b.color = (1, 0, 0, b.power ** 0.5)
        if b.power < 0.01:
            b.delete()
            bullets.remove(b)


run()
