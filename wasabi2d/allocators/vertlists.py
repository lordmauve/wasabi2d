import typing
from typing import Tuple
from dataclasses import dataclass
from collections import OrderedDict

import moderngl
import numpy as np

from .abstract import AbstractAllocator, NoCapacity


TYPE_MAP = {
    'uint8': 'f1',
    'uint16': 'u2',
    'uint32': 'u4',
    'uint64': 'u8',
    'int8': 'i1',
    'int16': 'i2',
    'int32': 'i4',
    'int64': 'i8',
    'float16': 'f2',
    'float32': 'f4',
    'float64': 'f8',
}


def dtype_to_moderngl(dtype: np.dtype) -> tuple:
    """Convert a numpy dtype object to a ModernGL buffer type."""
    names = dtype.names
    assert names is not None, "Only structured numpy dtypes are allowed."
    fields = dtype.fields
    out = []
    byte_pos = 0  # position of next field
    for n in names:
        dtype, offset, *_ = fields[n]

        out.extend('x' * (offset - byte_pos))
        byte_pos = offset + dtype.itemsize

        type_name = TYPE_MAP[dtype.base.name]
        assert len(dtype.shape) <= 1, \
            "Multi-dimensional dtypes are not supported."
        if dtype.shape == ():
            out.append(type_name)
        else:
            out.append(f'{dtype.shape[0]}{type_name}')
    return (' '.join(out), *names)


@dataclass(eq=False)
class VAOList:
    """A list allocated within a VAO."""
    buf: 'VAO'
    command: int

    # View of the vertex buffer, and slice
    vertbuf: np.ndarray
    vertoff: slice

    # View of the index buffer, and slice
    indexbuf: np.ndarray
    indexoff: slice

    # Number of verts and indexes in the allocation
    _hwm_verts: int
    _hwm_indexes: int

    #: True if needs syncing to the GL
    dirty: bool = False

    @property
    def num_indexes(self):
        """Get the number of indices to draw."""
        pos = self.buf.allocs.index(self)
        return self.buf.indirect[pos, 0]

    @num_indexes.setter
    def num_indexes(self, n):
        """Set the number of indices to draw.

        If a larger segment is allocated, this can be used to very cheaply
        resize it.

        It is not yet supported to resize the index allocation at this point.
        """
        size = len(self.indexbuf)
        if n > size:
            raise ValueError(f"Only allocated {size} indices.")

        # TODO: linear cost
        pos = self.buf.allocs.index(self)
        self.buf.indirect[pos, 0] = n

    def realloc(self, num_verts=None, num_indexes=None):
        """Reallocate the list to a new size. Invalidate the data."""
        if num_verts is None:
            num_verts = len(self.vertbuf)
        if num_indexes is None:
            num_indexes = len(self.indexbuf)

        if num_verts == len(self.vertbuf) \
                and num_indexes == len(self.indexbuf):
            return
        self.buf.realloc(self, num_verts, num_indexes)

    def free(self):
        if self.buf:
            self.buf.free(self)

    __del__ = free


class IndirectBuffer:
    """Abstraction over managing indirect allocations.

    Indirect draw commands always have the same 5 u4 parameters:

    (count, instanceCount, firstIndex, baseVertex, baseInstance)

    """
    def __init__(self, ctx, capacity=50):
        self.ctx = ctx
        self.capacity = capacity
        self.next_key = 0
        self.allocations = OrderedDict()
        self.buffer = None

    def _initialise(self):
        self.indirect = np.zeros((self.capacity, 5), dtype='u4')
        for aidx, lst in enumerate(self.allocs):
            num_indexes = lst.indexoff.stop - lst.indexoff.start
            ixs_start = lst.indexoff.start
            vs_start = lst.vertoff.start
            self.indirect[aidx] = (num_indexes, 1, ixs_start, vs_start, 0)
        self.buffer = self.ctx.buffer(self.indirect, dynamic=True)
        self.dirty = False

    def get_buffer(self):
        """Get the buffer object.

        Create a new buffer object if dirty.

        """
        if not self.buffer:
            self.buffer = self.ctx.buffer(
                np.array(list(self.allocations.values()), dtype='u4'),
            )
        return self.buffer

    def render_direct(self, vao, mode):
        cmds = self.allocations.values()
        for vs, insts, base_idx, base_v, base_inst in cmds:
            vao.render(mode, vs, first=base_idx, instances=1)

    def append(self, vs, insts, base_idx, base_v, base_inst) -> int:
        """Append an indirect draw command.

        Return an opaque key that can be used to update or delete the command.
        """
        assert base_v == 0
        key = self.next_key
        self.next_key += 1

        self.allocations[key] = np.array(
            [vs, insts, base_idx, base_v, base_inst],
            dtype='u4'
        )
        self.buffer = None
        return key

    def __delitem__(self, key):
        del self.allocations[key]
        self.buffer = None

    def __setitem__(self, key, vals):
        assert len(vals) == 5, "Invalid indirect draw command"
        self.allocations[key][:] = vals
        self.buffer = None


class MemoryBackedBuffer:
    """Maintain a GL buffer plus a numpy arrays for storage."""

    def __init__(self, ctx, capacity, dtype):
        self.ctx = ctx
        self.allocator = AbstractAllocator(capacity)
        self.dtype = dtype
        self.array = np.empty(capacity, dtype=self.dtype)
        self.buffer = None

    def allocate(self, num: int) -> Tuple[slice, np.ndarray]:
        """Allocate a slice of the array.

        Return a slice and view.

        """
        try:
            allocated = self.allocator.alloc(num)
        except NoCapacity as e:
            new_size = e.recommended
            new_array = np.empty(new_size, dtype=self.dtype)
            new_array[:len(self.array)] = self.array
            self.array = new_array
            self.allocator.grow(e.recommended)
            self.buffer = None
            allocated = self.allocator.alloc(num)
        return allocated, self.array[allocated]

    def get_buffer(self, dirty=False) -> moderngl.Buffer:
        """Get the buffer."""
        if not self.buffer:
            self.buffer = self.ctx.buffer(self.array, dynamic=True)
        elif dirty:
            self.buffer.write(self.array)
        return self.buffer

    def realloc(self, offset: slice, size: int) -> Tuple[slice, np.ndarray]:
        """Resize the allocation at offset. Return the new slice and view."""
        # TODO: use self.allocator.realloc here
        self.allocator.free(offset)
        newoff, new_view = self.allocate(size)
        copy_size = min(size, offset.stop - offset.start)
        new_view[:copy_size] = self.array[offset][:copy_size]
        return newoff, new_view

    def free(self, offset: typing.Union[int, slice]):
        """Free the allocation."""
        self.allocator.free(offset)


class VAO:
    """Manage vertex lists within a VAO."""

    def __init__(
            self,
            mode: int,
            ctx: moderngl.Context,
            prog: moderngl.Program,
            dtype: np.dtype,
            capacity: int = 4096,
            index_capacity: int = 8192):
        self.mode = mode
        self.ctx = ctx
        self.prog = prog
        self.dtype = dtype_to_moderngl(dtype)
        self.verts = MemoryBackedBuffer(ctx, capacity, dtype)
        self.indexes = MemoryBackedBuffer(ctx, index_capacity, 'i4')
        self.indirect = IndirectBuffer(ctx)
        self.allocs: typing.List[VAOList] = []
        self.vao = None

    def _initialise(self):
        """Create OpenGL objects."""
        self.vbo = self.verts.get_buffer()
        self.ibo = self.indexes.get_buffer()
        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo, *self.dtype),
            ],
            self.ibo
        )

    def alloc(self, num_verts: int, num_indexes: int) -> VAOList:
        """Allocate a list from within this buffer."""
        vs, vertbuf = self.verts.allocate(num_verts)
        ixs, indexbuf = self.indexes.allocate(num_indexes)

        cmd = self.indirect.append(num_indexes, 1, ixs.start, 0, 0)
        lst = VAOList(
            buf=self,
            command=cmd,
            vertbuf=vertbuf,
            vertoff=vs,
            indexbuf=indexbuf,
            indexoff=ixs,
            _hwm_verts=num_verts,
            _hwm_indexes=num_indexes,
            dirty=True
        )
        self.allocs.append(lst)
        return lst

    def realloc(self, lst: VAOList, num_verts: int, num_indexes: int):
        """Reallocate a list, typically to grow the size of it.

        Data will be copied to the new list and it will retain its draw
        order.

        We maintain high water marks on the allocation for a list and will
        shrink an existing numpy slice without going back to the allocator.
        When we do go back, we ask for extra.
        """
        need_verts = num_verts != len(lst.vertbuf)
        need_idxs = num_indexes != len(lst.indexbuf)

        if need_verts:
            lst.vertoff, lst.vertbuf = self.verts.realloc(
                lst.vertoff,
                num_verts,
            )
        if need_idxs:
            lst.indexoff, lst.indexbuf = self.indexes.realloc(
                lst.indexoff,
                num_indexes,
            )

        lst.dirty = True
        self.indirect[lst.command] = (
            num_indexes,
            1,
            lst.indexoff.start,
            lst.vertoff.start,
            0
        )

    def free(self, lst):
        """Remove a list from the array."""
        self.allocs.remove(lst)
        del self.indirect[lst.command]

        # Free space in allocators
        self.verts.free(lst.vertoff)
        self.indexes.free(lst.indexoff)

        lst.buf = None
        lst.vertbuf = None
        lst.indexbuf = None

    def get_vao(self):
        # TODO: use the dirty list to more accurately indicate which parts of
        # a buffer need updating.
        dirty = False
        for a in self.allocs:
            if a.dirty:
                dirty = True
                a.dirty = False

        vbo = self.verts.get_buffer(dirty)
        ibo = self.indexes.get_buffer(dirty)

        # TODO: only recreate the VAO if buffers have changed
        vao = self.ctx.vertex_array(
            self.prog,
            [
                (vbo, *self.dtype),
            ],
            ibo
        )
        return vao

    def render(self):
        """Render all lists."""
        if not self.allocs:
            return
        vao = self.get_vao()
        if self.ctx.version_code >= 400:
            indirect = self.indirect.get_buffer()
            vao.render_indirect(
                indirect,
                mode=self.mode,
            )
        else:
            self.indirect.render_direct(vao, self.mode)
