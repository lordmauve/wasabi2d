"""Example of the sepia effect."""
import wasabi2d as w2d

scene = w2d.Scene()

photo = scene.layers[0].add_sprite(
    'positano',
    pos=(scene.width / 2, scene.height / 2),
)
photo.scale = max(
    scene.width / photo.width,
    scene.height / photo.height
)
effect = scene.layers[0].set_effect('posterize')

levels_label = scene.layers[1].add_label(
    f'Levels: {effect.levels}',
    align='center',
    pos=(scene.width / 2, scene.height - 40),
    color='white',
    fontsize=20,
)
gamma_label = scene.layers[1].add_label(
    f'Gamma: {effect.gamma:0.2f}',
    align='center',
    pos=(scene.width / 2, scene.height - 20),
    color='white',
    fontsize=20,
)
scene.layers[1].set_effect('dropshadow', radius=2)


@w2d.event
def on_mouse_move(pos):
    x, y = pos
    fracx = x / scene.width
    fracy = y / scene.height
    effect.levels = round(18 * fracx) + 1
    effect.gamma = 0.2 + 2 * fracy
    levels_label.text = f'Levels: {effect.levels}'
    gamma_label.text = f'Gamma: {effect.gamma:0.2f}'


w2d.run()
