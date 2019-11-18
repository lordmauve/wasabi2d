"""Example of using one layer to lens another."""
import wasabi2d as w2d
import pygame.surface
import pygame.surfarray
import pygame.image
from pathlib import Path
import numpy as np

scene = w2d.Scene()
center = (scene.width / 2, scene.height / 2)

photo = scene.layers[0].add_sprite(
    'positano',
    pos=center
)
photo.scale = max(
    scene.width / photo.width,
    scene.height / photo.height
)


def make_lens():
    sz = 800
    surf = pygame.Surface((sz, sz), depth=32, flags=pygame.SRCALPHA)
    center = sz * 0.5
    for y in range(sz):
        for x in range(sz):
            off = np.array([x, sz - y]) - center
            off /= center

            dist = np.sum(off * off)
            color = (
                *np.clip(127.5 - 64 * off - 64 * off * dist, 0, 255),
                dist,
                0 if dist > 1 else 255
            )
            surf.set_at((x, y), color)
    surf = pygame.transform.smoothscale(surf, (200, 200))
    pygame.image.save(surf, str(Path(__file__).parent / 'images/lens.png'))


#make_lens()

lens = scene.layers[1].add_sprite(
    'lens_8x',
    pos=center,
)

scene.chain = [
    w2d.chain.LayerRange(stop=0),
    w2d.chain.DisplacementMap(
        displacement=w2d.chain.Layers([1]),
        paint=w2d.chain.LayerRange(stop=0),
        scale=400
    )
]


@w2d.event
def on_mouse_move(pos):
    lens.pos = pos


w2d.run()
