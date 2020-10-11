import random
import wasabi2d as w2d
import colorsys
from wasabi2d import clock, vec2, animate


scene = w2d.Scene(title="Run!")
center = vec2(scene.width, scene.height) / 2
scene.background = 'white'
target = vec2(scene.width, scene.height) / 2
scene.layers[0].set_effect('dropshadow', opacity=1, radius=1)


cursor = scene.layers[0].add_polygon(
    [(0, 0), (-15, 5), (-13, 0), (-15, -5)],
    fill=False,
    color='black',
    stroke_width=3,
)
cursor.angle = 4


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

    scene.camera.screen_shake()
    await animate(
        e,
        duration=0.1,
        scale=10,
        tween='accelerate',
        color=(*color, 0)
    )
    e.delete()


@w2d.event
def on_mouse_move(pos):
    global target
    cursor.pos = pos
    target = vec2(pos)


async def spawn_baddies():
    async with w2d.Nursery() as ns:
        ns.do(enemy())
        for _ in range(5):
            await clock.coro.sleep(2)
            ns.do(enemy())

    scene.layers[0].add_label(
        "The End",
        align="center",
        fontsize=48,
        color='#88ccff',
        pos=center
    )
    await clock.coro.sleep(5)


w2d.run(spawn_baddies())
