"""Render the nine-patch examples used by the documentation."""
from pathlib import Path

import pygame.image
import pygame.transform

import wasabi2d as w2d
from wasabi2d.loaders import images
from wasabi2d.scene import HeadlessScene, capture_screen


DOCS = Path(__file__).parents[1]
SOURCE = DOCS / '_static' / 'primitives' / 'ninepatch-panel.png'
OUTPUT = DOCS / '_static' / 'primitives' / 'ninepatch-examples.png'


def render():
    scene = HeadlessScene(width=1600, height=1000, rootdir=DOCS)
    try:
        scene.background = '#101521'
        source = pygame.image.load(str(SOURCE))
        if source.get_size() != (480, 282):
            source = source.subsurface((36, 58, 1464, 862))
            source = pygame.transform.smoothscale(source, (480, 282))
            pygame.image.save(source, str(SOURCE))
        images._cache[images.cache_key('ninepatch_panel', (), {})] = source

        panel = w2d.NinePatch(
            'ninepatch_panel',
            hcuts=(55, 425),
            vcuts=(48, 238),
        )
        layer = scene.layers[0]

        layer.add_ninepatch(
            panel,
            pos=(520, 270),
            width=1500,
            height=650,
            scale=0.6,
        )
        layer.add_label(
            'QUEST COMPLETE',
            pos=(520, 190),
            align='center',
            fontsize=42,
            color='#ffd77a',
        )
        layer.add_label(
            'The old observatory is open.',
            pos=(520, 270),
            align='center',
            fontsize=30,
            color='white',
        )

        layer.add_ninepatch(
            panel,
            pos=(460, 715),
            width=1050,
            height=330,
            scale=0.52,
        )
        layer.add_label(
            'CONTINUE',
            pos=(460, 715),
            align='center',
            fontsize=42,
            color='white',
        )

        layer.add_ninepatch(
            panel,
            pos=(1280, 500),
            width=900,
            height=1550,
            scale=0.54,
        )
        layer.add_label(
            'INVENTORY',
            pos=(1280, 210),
            align='center',
            fontsize=38,
            color='#ffd77a',
        )
        for y, text in zip(
            (330, 430, 530, 630),
            ('Brass key', 'Moonstone', 'Field notes', 'Travel cloak'),
        ):
            layer.add_label(
                text,
                pos=(1280, y),
                align='center',
                fontsize=27,
                color='white',
            )

        scene.draw(0, 0, True)
        pygame.image.save(capture_screen(scene.ctx.screen), str(OUTPUT))
    finally:
        scene.release()


if __name__ == '__main__':
    render()
