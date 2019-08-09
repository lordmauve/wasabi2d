import math
import pygame
import moderngl
from pyrr import Matrix44, Vector3, vector3, matrix33
from dataclasses import dataclass, field

from wasabi2d import event, run
from wasabi2d import LayerGroup


pygame.init()
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
pygame.display.gl_set_attribute(
    pygame.GL_CONTEXT_PROFILE_MASK,
    pygame.GL_CONTEXT_PROFILE_CORE
)
screen = pygame.display.set_mode(
    (1600, 1200),
    flags=pygame.OPENGL | pygame.DOUBLEBUF,
    depth=24
)
ctx = moderngl.create_context()


layers = LayerGroup(ctx)
ship = layers[0].add_sprite('ship.png')


t = 0


proj = Matrix44.orthogonal_projection(
    left=0, right=800, top=600, bottom=0, near=-1000, far=1000,
).astype('f4')
ctx.enable(moderngl.BLEND)
ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

ship_pos = Vector3()
ship_v = Vector3()


bullets = []


@event
def on_mouse_down(pos):
    print(pos)


@event
def on_key_down(key):
    if key == key.SPACE:
        bullet = layers[0].add_sprite('tiny_bullet.png', pos=ship.pos)
        bullet.color = (1, 0, 0, 1)
        bullet.vel = vector3.normalize(ship_v)[:2] * 600
        bullet.power = 1.0
        bullets.append(bullet)


@event
def update(dt, keyboard):
    global ship_v, ship_pos
    ship_v *= 0.3 ** dt

    accel = 300 * dt
    if keyboard.right:
        ship_v[0] += accel
    elif keyboard.left:
        ship_v[0] -= accel
    if keyboard.up:
        ship_v[1] -= accel
    elif keyboard.down:
        ship_v[1] += accel

    ship_vx, ship_vy, _ = ship_v
    ship_pos += ship_v * dt

    ship.pos = ship_pos[:2]
    if not (-1e-6 < ship_vx < 1e-6 and -1e-6 < ship_vy < -1e-6):
        ship.angle = math.atan2(ship_vy, ship_vx)

    for b in bullets.copy():
        b.pos += b.vel * dt
        b.power = max(0, b.power - dt)
        b.angle += 3 * dt
        b.scale = b.power
        b.color = (1, 0, 0, b.power ** 0.5)
        if b.scale < 0.01:
            b.delete()
            bullets.remove(b)


@event
def draw(t, dt):
    layers.render(proj, t, dt)


run()
