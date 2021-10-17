import wasabi2d as w2d
import pygame


scene = w2d.Scene()

particles = scene.layers[0].add_particle_group(
    max_age=2,
    grow=0.1,
)

async def particle_spray():
    ev = await w2d.next_event(pygame.MOUSEBUTTONDOWN)
    emitter = particles.add_emitter(
        pos=ev.pos,
        rate=50,
        color='cyan',
        size=6,
        vel_spread=30
    )
    async for ev in w2d.events.subscribe(pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
        if ev.type == pygame.MOUSEBUTTONUP:
            emitter.delete()
            return
        else:
            emitter.pos = ev.pos

async def main():
    while True:
        await particle_spray()

w2d.run(main())
