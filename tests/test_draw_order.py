"""Draw scheduling and buffer submission, without an OpenGL context."""
import gc
import weakref
from unittest.mock import Mock

import moderngl
import numpy as np
import pytest

from wasabi2d.allocators.index import IndexBuffer, merge_draws
from wasabi2d.allocators.packed import PackedBuffer
from wasabi2d.allocators.vertlists import VAO
from wasabi2d.layers import Layer
from wasabi2d.primitives.base import ZOrder


DTYPE = np.dtype([('in_vert', '2f4')])


def make_buffer(ctx, packed):
    cls = PackedBuffer if packed else VAO
    return cls(moderngl.TRIANGLES, ctx, Mock(), DTYPE)


def allocate(buffer, key):
    if isinstance(buffer, PackedBuffer):
        id, _ = buffer.alloc(3, np.arange(3, dtype='u4'))
    else:
        allocation = buffer.alloc(3, 3)
        allocation.indexbuf[:] = np.arange(3) + allocation.vertoff.start
        id = allocation.command
    buffer.set_sort(id, key)
    return id


def schedule(*buffers):
    for buffer in buffers:
        buffer.set_zsorted(True)
    return list(merge_draws(b.iter_draws() for b in buffers))


@pytest.mark.parametrize('packed', [False, True])
def test_sort_toggle_and_dynamic_allocations(packed):
    buffer = make_buffer(Mock(), packed)
    ids = [allocate(buffer, (z, i)) for i, z in enumerate([1, -1, 0])]
    buffer.set_zsorted(True)
    assert [key for key, *_ in buffer.iter_draws()] == [(-1, 1), (0, 2), (1, 0)]
    buffer.set_sort(ids[0], (-2, 0))
    assert [key for key, *_ in buffer.iter_draws()] == [(-2, 0), (-1, 1), (0, 2)]
    # Allocating into an already sorted buffer must not compare None to tuples.
    allocate(buffer, (0, 3))
    assert [key for key, *_ in buffer.iter_draws()] == [(-2, 0), (-1, 1), (0, 2), (0, 3)]
    buffer.set_zsorted(False)
    if packed:
        assert list(buffer.indexes.id_lookup) == list(range(1, 5))
        assert [key[1] for key in buffer.indexes.allocations] == list(range(1, 5))
    else:
        assert buffer.indirect.ordered_keys() == list(range(4))


def test_merge_across_buffer_types_batches_contiguous_ranges():
    ctx = Mock()
    sprites, shapes = make_buffer(ctx, True), make_buffer(ctx, False)
    for key in [(0, 0), (0, 2), (0, 3)]:
        allocate(sprites, key)
    for key in [(0, 1), (0, 4)]:
        allocate(shapes, key)
    assert schedule(sprites, shapes) == [
        (sprites, 0, 3), (shapes, 0, 1), (sprites, 3, 9), (shapes, 1, 2),
    ]


@pytest.mark.parametrize('version', [410, 450])
def test_legacy_render_submits_only_selected_sorted_commands(version):
    ctx = Mock(version_code=version)
    buffer = make_buffer(ctx, False)
    allocate(buffer, (2, 0))
    allocate(buffer, (0, 1))
    allocate(buffer, (1, 2))
    buffer.set_zsorted(True)
    vao = Mock()
    buffer.render(None, first=1, count=1, vao=vao)
    if version >= 420:
        vao.render_indirect.assert_called_once_with(
            buffer.indirect.get_buffer(), mode=moderngl.TRIANGLES, first=1, count=1,
        )
        # The uploaded command array must have the same order as the schedule.
        commands = ctx.buffer.call_args.args[0]
        expected = [buffer.indirect.allocations[k] for k in [1, 2, 0]]
        np.testing.assert_array_equal(commands, expected)
    else:
        vao.render.assert_called_once_with(
            moderngl.TRIANGLES, 3,
            first=buffer.allocs[2].indexoff.start, instances=1,
        )
    vao.release.assert_not_called()


def test_packed_render_submits_only_selected_indices():
    buffer = make_buffer(Mock(), True)
    allocate(buffer, (0, 0))
    allocate(buffer, (0, 1))
    vao = Mock()
    buffer.render(None, first=3, count=3, vao=vao)
    vao.render.assert_called_once_with(moderngl.TRIANGLES, first=3, vertices=3)
    vao.release.assert_not_called()


def test_cached_schedule_survives_vertex_changes_but_not_z_changes():
    ctx = Mock()
    ctx.vertex_array.side_effect = lambda *a, **kw: Mock()
    layer = Layer(ctx, Mock())
    a, b = make_buffer(ctx, True), make_buffer(ctx, True)
    first = allocate(a, (0, 0))
    allocate(b, (0, 1))
    allocate(a, (0, 2))
    layer.arrays['a'], layer.arrays['b'] = a, b
    layer.zsorted = True
    layer._draw_sorted(None)
    commands = layer._draw_commands
    assert len(commands) == 3
    assert ctx.vertex_array.call_count == 2  # a is prepared once, despite two draws
    a.get_verts(first)['in_vert'] = 1
    layer._draw_sorted(None)
    assert layer._draw_commands is commands
    a.set_sort(first, (1, 0))
    layer._draw_sorted(None)
    assert layer._draw_commands is not commands
    assert len(layer._draw_commands) == 2
    commands = layer._draw_commands
    a.remove(first)
    layer._draw_sorted(None)
    assert layer._draw_commands is not commands
    a_ref = weakref.ref(a)
    del a
    gc.collect()
    assert a_ref() is None  # the cache must not retain otherwise-unused buffers
    assert 'a' not in layer.arrays


def test_sorted_vao_cleanup_on_draw_error():
    ctx = Mock()
    layer = Layer(ctx, Mock())
    buffer = make_buffer(ctx, True)
    allocate(buffer, (0, 0))
    layer.arrays[0] = buffer
    ctx.vertex_array.return_value.render.side_effect = RuntimeError('draw failed')
    with pytest.raises(RuntimeError, match='draw failed'):
        layer._draw_sorted(None)
    ctx.vertex_array.return_value.release.assert_called_once()


def test_index_buffer_upload_is_cached_and_invalidated():
    ctx = Mock()
    buffer = IndexBuffer(ctx)
    id = buffer.insert(np.arange(3, dtype='u4'), 1)
    uploaded = buffer.get_buffer()
    assert buffer.get_buffer() is uploaded
    assert ctx.buffer.call_count == 1
    buffer.set_sort(id, -1)
    buffer.get_buffer()
    assert ctx.buffer.call_count == 2
    buffer.clear()
    assert buffer.as_array().dtype == np.uint32
    assert buffer.insert(np.arange(1, dtype='u4')) == 1


def test_z_validation_and_stable_creation_order():
    a, b = ZOrder(), ZOrder()
    assert a.z == b.z == 0
    assert a._sort_key < b._sort_key
    for bad in [float('inf'), -float('inf'), float('nan')]:
        with pytest.raises(ValueError):
            a.z = bad
    with pytest.raises(TypeError):
        a.z = 'front'
    a.z = -2.5
    assert a._sort_key < b._sort_key


def test_num_indexes_uses_allocation_id_after_sorting_and_deletion():
    buffer = make_buffer(Mock(), False)
    allocate(buffer, (0, 0))
    allocate(buffer, (-1, 1))
    second = buffer.allocs[1]
    buffer.free(buffer.allocs[0])
    buffer.set_zsorted(True)
    second.num_indexes = 2
    assert second.num_indexes == 2
    assert buffer.indirect.allocations[second.command][0] == 2
