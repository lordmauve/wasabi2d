import random
import wasabi2d as w2d
import colorsys
from wasabi2d import clock, Vector2, animate, keyboard


scene = w2d.Scene(title="Run!")
scene.background = 'white'
target = Vector2(scene.width / 2, scene.height / 2)
scene.layers[0].set_effect('dropshadow', opacity=1, radius=1)


async def spawn_baddies():
    while True:
        clock.coro.run(enemy())
        await clock.coro.sleep(3)


async def enemy():
    color = colorsys.hsv_to_rgb(random.random(), 1, 1)
    pos = Vector2(
        random.uniform(50, scene.width - 50),
        random.uniform(50, scene.height - 50)
    )
    e = scene.layers[0].add_circle(
        radius=10,
        color=color,
        pos=pos,
    )
    e.scale = 0.1
    await animate(
        e,
        duration=0.3,
        scale=1,
    )
    async for dt in clock.coro.frames_dt():
        to_target = target - pos
        if to_target.magnitude() < e.radius:
            break
        pos += to_target.normalize() * 100 * dt
        e.pos = pos

    await animate(
        e,
        duration=0.5,
        scale=4,
        tween='accelerate',
        color=(*color, 0)
    )

    e.delete()


@w2d.event
def on_mouse_move(pos):
    global target
    target = Vector2(*pos)


clock.coro.run(spawn_baddies())
w2d.run()
