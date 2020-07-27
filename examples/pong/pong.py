import wasabi2d as w2d
import random
from pygame.math import Vector2
from wasabi2d.keyboard import keys
from wasabi2d import chain

from pygame import joystick


CYAN = (0, 1, 1)
RED = (1, 0.2, 0.2)

mode_1080p = 1920, 1080
scene = w2d.Scene(
    *mode_1080p,
    fullscreen=True,
)
scene.chain = [
    chain.Light(
        light=[
            chain.Layers([99]),
        ],
        diffuse=[
            chain.Fill('#444455'),
            chain.LayerRange(stop=10),
        ],
        ambient='#222222'
    )
]


center = Vector2(scene.width, scene.height) / 2

red_score = scene.layers[-1].add_label(
    0,
    pos=(30, 100),
    font="bitwise",
    fontsize=100,
    align="left",
    color=(2, 0, 0)
)

blue_score = scene.layers[-1].add_label(
    0,
    pos=(scene.width, 100),
    font="bitwise",
    fontsize=100,
    align="right",
    color=CYAN
)

red = w2d.Group(
    [
        scene.layers[0].add_sprite('bat_red'),
        scene.layers[99].add_sprite('bat_light', color=(*RED, 0.5)),
    ],
    pos=(100, center.y))

red.up_key = keys.Q
red.down_key = keys.A

blue = w2d.Group(
    [
        scene.layers[0].add_sprite('bat_blue'),
        scene.layers[99].add_sprite('bat_light', color=(*CYAN, 0.5)),
    ],
    pos=(scene.width - 100, center.y)
)
blue.up_key = keys.I
blue.down_key = keys.K

particles = scene.layers[-1].add_particle_group(max_age=2, drag=0.2, grow=0.1)
particles.add_color_stop(0, (1, 1, 1, 1))
particles.add_color_stop(2, (1, 1, 1, 0))

ball = w2d.Group(
    [
        scene.layers[0].add_sprite('ball'),
        scene.layers[99].add_sprite('point_light', scale=5, color=(1, 1, 1, 0.3)),
        particles.add_emitter(
            rate=0,
            size=3,
            pos_spread=8,
            vel_spread=30
        )
    ],
    pos=center
)
ball.emitter = ball[2]
ball.vel = Vector2(0, 0)

SPEED = 1000
BALL_RADIUS = ball[0].width / 2


for bat in (red, blue):
    bat.last_y = bat.y


async def start(x_dir=None):
    ball.emitter.rate = 0
    ball.pos = center
    ball.vel = Vector2(0, 0)
    ball.scale = 0.1
    await w2d.animate(ball, scale=1.0)
    ball.emitter.rate = 30
    ball.vel = Vector2(
        random.choice([SPEED, -SPEED]) if x_dir is None else SPEED * x_dir,
        random.uniform(SPEED, -SPEED),
    )


SPIN = -8


def collide_bat(bat):
    bounds = bat[0].bounds.inflate(BALL_RADIUS, BALL_RADIUS)
    if bounds.collidepoint(ball.pos):
        bat_vy = bat.y - bat.last_y
        x, y = ball.pos
        vx, vy = ball.vel
        if x < bat.x:
            ball.vel = Vector2(-abs(vx), vy + bat_vy * SPIN)
        else:
            ball.vel = Vector2(abs(vx), vy + bat_vy * SPIN)


@w2d.event
def update(dt, keyboard):
    ball.pos += ball.vel * dt
    x, y = ball.pos
    if y < BALL_RADIUS:
        ball.vel.y = abs(ball.vel.y)
    elif y > scene.height - BALL_RADIUS:
        ball.vel.y = -abs(ball.vel.y)

    if x < -BALL_RADIUS:
        scene.camera.screen_shake()
        blue_score.text += 1
        w2d.clock.coro.run(start(1))
    elif x > scene.width + BALL_RADIUS:
        w2d.clock.coro.run(start(-1))
        scene.camera.screen_shake()
        red_score.text += 1

    for stick, bat in zip(sticks, (red, blue)):
        sy = stick.get_axis(1)
        w2d.animate(bat, duration=0.1, y=center.y + sy * (center.y - 40))

    for bat in (red, blue):
        if keyboard[bat.up_key]:
            bat.y -= SPEED * dt
        elif keyboard[bat.down_key]:
            bat.y += SPEED * dt

        collide_bat(bat)
        bat.last_y = bat.y


joystick.init()
sticks = [joystick.Joystick(i) for i in range(min(joystick.get_count(), 2))]
for s in sticks:
    s.init()


@w2d.event
def on_joybutton_down(joy, button):
    #print(joy, button)
    if button == 6:
        red_score.text = blue_score.text = 0
        w2d.clock.coro.run(start())


w2d.run()
