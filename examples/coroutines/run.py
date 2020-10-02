import random
import wasabi2d as w2d
import colorsys
from wasabi2d import clock, vec2, animate, keyboard, gather


scene = w2d.Scene(title="Run!")
scene.background = 'white'
target = vec2(scene.width, scene.height) / 2
scene.layers[0].set_effect('dropshadow', opacity=1, radius=1)


async def spawn_baddies():
    coros = [enemy() for _ in range(10)]
    await gather(*coros)


async def enemy():
    color = colorsys.hsv_to_rgb(random.random(), 1, 1)
    pos = vec2(
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
        if to_target.length() < e.radius:
            break
        pos += to_target.scaled_to(100 * dt)
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
    target = vec2(pos)


w2d.run(spawn_baddies())
