import wasabi2d as w2d
import pygame._sdl2.touch
import random
import colorsys
from wasabi2d import vec2


scene = w2d.Scene(1280, 720, background='white')
scene.chain = [
    w2d.chain.LayerRange().wrap_effect('outline')
]
particles = scene.layers[0].add_particle_group(
    max_age=2,
    grow=0.2,
    gravity=vec2(0, -200),
    drag=0.5,
)


def pos(touch_event):
    return w2d.vec2(touch_event.x * scene.width, touch_event.y * scene.height)


async def next_touch():
    touch = w2d.events.subscribe(
        pygame.FINGERDOWN,
        pygame.FINGERMOTION,
        pygame.FINGERUP,
    )
    async for ev in touch:
        if ev.type == pygame.FINGERDOWN:
            finger_id = ev.finger_id
            touch_start = pos(ev)
            break

    async def positions():
        yield pos(touch_start)
        async for ev in touch:
            if ev.finger_id != finger_id:
                continue
            if ev.type == pygame.FINGERUP:
                return
            else:
                yield pos(ev)
    return positions()


async def run_touch(initial_pos, touch_events):
    color = colorsys.hsv_to_rgb(random.random(), 1, 1)
    emitter = particles.add_emitter(
        pos=initial_pos,
        rate=200,
        color=color,
        size=12,
        vel_spread=60,
        pos_spread=10,
    )
    try:
        async for ev in touch_events:
            emitter.pos = pos(ev)
    finally:
        emitter.delete()


async def main():
    async with w2d.Nursery() as nursery:
        while True:
            touch = w2d.events.next_touch()
            first_ev = await anext(touch)
            nursery.do(run_touch(pos(first_ev), touch))


w2d.run(main())
