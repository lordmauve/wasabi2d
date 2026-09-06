"""Pixel comparisons of sorted layers against separately ordered layers."""
import numpy as np
import pygame
import pytest

from wasabi2d import NinePatch, chain


@pytest.fixture(params=[410, 450], ids=['direct', 'indirect'])
def renderer(scene, request):
    """Exercise the macOS fallback and indirect submission on the same GPU."""
    original = scene.ctx.version_code
    if request.param >= 420 and original < 420:
        pytest.skip('Indirect rendering requires OpenGL 4.2')
    scene.ctx.version_code = request.param
    scene.background = (0.1, 0.15, 0.2)
    # Identical images on different textures let migration change batching
    # without changing the expected pixels.
    surface = pygame.Surface((64, 64), pygame.SRCALPHA)
    surface.fill((255, 255, 255, 255))
    atlas = scene.layers.atlas
    for name in ['solid_a', 'solid_b']:
        atlas.npot_tex(name, surface)
    yield scene
    for layer in list(scene.layers.values()):
        for obj in list(layer.objects):
            obj.delete()
    scene.ctx.version_code = original


def make(layer, kind, color=(0.8, 0.2, 0.3, 0.6)):
    pos = (100, 100)
    if kind == 'sprite':
        return layer.add_sprite('solid_a', pos=pos, scale=2, color=color)
    if kind == 'other_texture':
        return layer.add_sprite('solid_b', pos=pos, scale=2, color=color)
    if kind == 'rect':
        return layer.add_rect(110, 90, pos=pos, color=color)
    if kind == 'circle':
        return layer.add_circle(radius=65, pos=pos, color=color)
    if kind == 'line':
        return layer.add_line([(40, 40), (100, 120), (160, 60)],
                              stroke_width=25, color=color)
    if kind == 'label':
        return layer.add_label('MMM', pos=(30, 120), fontsize=60, color=color)
    if kind == 'ninepatch':
        return layer.add_ninepatch(NinePatch('solid_a', (8, 56), (8, 56)),
                                   pos=pos, width=110, height=90, color=color)
    if kind == 'particles':
        group = layer.add_particle_group(max_age=10)
        group.emit(1, pos=pos, size=80, color=color)
        return group
    if kind == 'tilemap':
        tiles = layer.add_tile_map()
        tiles[1, 1] = 'solid_a'
        return tiles
    raise AssertionError(kind)


def pixels(scene, nodes):
    scene.chain = nodes
    scene.draw(0, 0, True)
    return np.frombuffer(scene.ctx.screen.read(components=3), dtype=np.uint8).astype(int)


def assert_matches_reference(scene, actual, expected, effect=False):
    actual_nodes = [0]
    expected_nodes = [100 + i for i in sorted(
        range(len(expected)), key=lambda i: (expected[i].z, i)
    )]
    if effect:
        actual_nodes = [chain.Effect(actual_nodes, 'greyscale', {})]
        expected_nodes = [chain.Effect(expected_nodes, 'greyscale', {})]
    a = pixels(scene, actual_nodes)
    b = pixels(scene, expected_nodes)
    assert np.max(np.abs(a - b)) <= 2
    assert np.any(a.reshape(-1, 3) != a[:3])


@pytest.mark.parametrize('kind', [
    'other_texture', 'rect', 'circle', 'line', 'label', 'ninepatch',
    'particles', 'tilemap',
])
@pytest.mark.parametrize('depths', [(0, 0, 0), (1, -2, 0.5)])
def test_interleaved_primitives_match_separate_layers(renderer, kind, depths):
    scene = renderer
    actual, expected = [], []
    for i, primitive in enumerate(['sprite', kind, 'sprite']):
        color = [(0.9, 0.2, 0.1, 0.6), (0.1, 0.9, 0.2, 0.7), (0.2, 0.1, 0.9, 0.5)][i]
        a = make(scene.layers[0], primitive, color)
        b = make(scene.layers[100 + i], primitive, color)
        a.z = b.z = depths[i]
        actual.append(a)
        expected.append(b)
    scene.layers[0].zsorted = True  # Enabling after creation must work too.
    assert_matches_reference(scene, actual, expected)
    # Updating z after the first draw must invalidate the cached schedule.
    actual[0].z = expected[0].z = -10
    assert_matches_reference(scene, actual, expected)


def test_migration_toggle_and_effect(renderer):
    scene = renderer
    layer = scene.layers[0]
    layer.zsorted = True
    actual, expected = [], []
    for i, kind in enumerate(['sprite', 'other_texture', 'ninepatch']):
        color = [(1, 0, 0, 0.6), (0, 1, 0, 0.6), (0, 0, 1, 0.6)][i]
        actual.append(make(layer, kind, color))
        expected.append(make(scene.layers[100 + i], kind, color))
    assert_matches_reference(scene, actual, expected)
    actual[0].image = 'solid_b'  # Migration must preserve the creation tie-break.
    actual[2].patch = NinePatch('solid_b', (8, 56), (8, 56))
    assert_matches_reference(scene, actual, expected)
    actual[2].z = expected[2].z = -1
    assert_matches_reference(scene, actual, expected, effect=True)
    layer.zsorted = False
    unsorted = pixels(scene, [0])
    layer.zsorted = True
    assert_matches_reference(scene, actual, expected)
    layer.zsorted = False
    np.testing.assert_array_equal(pixels(scene, [0]), unsorted)


def test_label_resize_empty_delete_and_recreate(renderer):
    scene = renderer
    layer = scene.layers[0]
    layer.zsorted = True
    actual, expected = [], []
    for i, kind in enumerate(['label', 'sprite', 'label']):
        actual.append(make(layer, kind))
        expected.append(make(scene.layers[100 + i], kind))
    assert_matches_reference(scene, actual, expected)
    actual[0].text = expected[0].text = 'A much longer label'
    assert_matches_reference(scene, actual, expected)
    actual[0].text = expected[0].text = ''
    assert_matches_reference(scene, actual, expected)
    actual[0].text = expected[0].text = 'MMM'
    assert_matches_reference(scene, actual, expected)
    actual[2].delete()
    expected[2].delete()
    actual[2] = make(layer, 'label', (0, 1, 0, 0.5))
    expected[2] = make(scene.layers[102], 'label', (0, 1, 0, 0.5))
    assert_matches_reference(scene, actual, expected)


def test_tilemap_delete_and_empty_sorted_layer(renderer):
    scene = renderer
    layer = scene.layers[0]
    layer.zsorted = True
    tilemap = make(layer, 'tilemap')
    pixels(scene, [0])
    tilemap.delete()
    empty = pixels(scene, [0])
    assert len(layer._draw_commands) == 0
    layer.clear()
    np.testing.assert_array_equal(pixels(scene, [0]), empty)
