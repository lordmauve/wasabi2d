import wasabi2d as w2d
import pygame
scene = w2d.Scene()

particles = scene.layers[0].add_particle_group(
    max_age=2,
    grow=0.1,
)

async def main():
    while True:
        ev = await w2d.next_event(pygame.MOUSEBUTTONDOWN)
        particles.emit(50, pos=ev.pos, vel_spread=30, size=6, color='cyan')

w2d.run(main())
