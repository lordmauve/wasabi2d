import typing
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
        self.buf.free(self)


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

    def append(self, vs, insts, base_idx, base_v, base_inst) -> int:
        """Append an indirect draw command.

        Return an opaque key that can be used to update or delete the command.
        """
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
        self.dtype = dtype
        self.allocator = AbstractAllocator(capacity)
        self.index_allocator = AbstractAllocator(index_capacity)
        self.allocs: typing.List[VAOList] = []
        self._initialise()

        self.indirect = IndirectBuffer(ctx)

    def _initialise(self):
        self.verts = np.zeros(self.allocator.capacity, dtype=self.dtype)
        self.indexes = np.zeros(self.index_allocator.capacity, dtype='i4')

        # Sync allocs into the new buffer
        for a in self.allocs:
            self.verts[a.vertoff] = a.vertbuf
            self.indexes[a.indexoff] = a.indexbuf
            a.vertbuf = self.verts[a.vertoff]
            a.indexbuf = self.indexes[a.indexbuf]
            a.dirty = False

        # Create OpenGL objects
        self.vbo = self.ctx.buffer(self.verts, dynamic=True)
        self.ibo = self.ctx.buffer(self.indexes, dynamic=True)
        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo, *dtype_to_moderngl(self.dtype)),
            ],
            self.ibo
        )

    def alloc(self, num_verts: int, num_indexes: int) -> VAOList:
        """Allocate a list from within this buffer."""
        vs, ixs = self._alloc_slices(num_verts, num_indexes)
        cmd = self.indirect.append(num_indexes, 1, ixs.start, vs.start, 0)
        lst = VAOList(
            buf=self,
            command=cmd,
            vertbuf=self.verts[vs],
            vertoff=vs,
            indexbuf=self.indexes[ixs],
            indexoff=ixs,
            _hwm_verts=num_verts,
            _hwm_indexes=num_indexes,
            dirty=True
        )
        self.allocs.append(lst)

        return lst

    def _alloc_verts(self, num_verts: int) -> slice:
        """Allocate a slice of vertices"""
        try:
            return self.allocator.alloc(num_verts)
        except NoCapacity as e:
            self.allocator.grow(e.recommended)
            self._initialise()
            return self.allocator.alloc(num_verts)

    def _alloc_indexes(self, num_indexes: int) -> slice:
        """Allocate a slice of indexes."""
        try:
            return self.index_allocator.alloc(num_indexes)
        except NoCapacity as e:
            self.index_allocator.grow(e.recommended)
            self._initialise()
            return self.index_allocator.alloc(num_indexes)

    def _alloc_slices(
            self,
            num_verts: int,
            num_indexes: int) -> typing.Tuple[slice, slice]:
        """Allocate slices of the vertex and index buffers.

        Return a tuple (verts, indexes), both slice objects.
        """
        grew = False
        try:
            vs = self.allocator.alloc(num_verts)
        except NoCapacity as e:
            self.allocator.grow(e.recommended)
            grew = True
            vs = self.allocator.alloc(num_verts)

        try:
            idxs = self.index_allocator.alloc(num_indexes)
        except NoCapacity as e:
            self.index_allocator.grow(e.recommended)
            grew = True
            idxs = self.index_allocator.alloc(num_indexes)

        if grew:
            self._initialise()
        return vs, idxs

    def realloc(self, lst: VAOList, num_verts: int, num_indexes: int):
        """Reallocate a list, typically to grow the size of it.

        Data will be copied to the new list and it will retain its draw
        order.

        We maintain high water marks on the allocation for a list and will
        shrink an existing numpy slice without going back to the allocator.
        When we do go back, we ask for extra.
        """
        pos = self.allocs.index(lst)

        vs = ixs = None
        need_verts = max(0, num_verts - lst._hwm_verts) * 4
        need_idxs = max(0, num_indexes - lst._hwm_indexes) * 4

        # TODO: this may be overcomplicated. We almost always need more
        # indices at the same time we need more vertices so the generality to
        # grow only one may be a net cost.

        if need_verts:
            self.allocator.free(lst.vertoff)
        if need_idxs:
            self.index_allocator.free(lst.indexoff)

        if need_verts and need_idxs:
            lst._hwm_verts += need_verts
            lst._hwm_indexes += need_idxs
            vs, ixs = self._alloc_slices(lst._hwm_verts, lst._hwm_indexes)
        elif need_verts:
            lst._hwm_verts += need_verts
            vs = self._alloc_verts(lst._hwm_verts)
        elif need_idxs:
            lst._hwm_indexes += need_idxs
            ixs = self._alloc_indexes(lst._hwm_indexes)

        if not vs:
            start = lst.vertoff.start
            vs = slice(start, start + num_verts)
        else:
            vs = slice(vs.start, vs.start + num_verts)
            # We still have a valid slice to copy to the new location
            self.verts[vs][:len(lst.vertbuf)] = lst.vertbuf

        if not ixs:
            start = lst.indexoff.start
            ixs = slice(start, start + num_indexes)
        else:
            ixs = slice(ixs.start, ixs.start + num_indexes)
            # We still have a valid slice to copy to the new location
            self.indexes[ixs][:len(lst.indexbuf)] = lst.indexbuf

        lst.vertbuf = self.verts[vs]
        lst.vertoff = vs
        lst.indexbuf = self.indexes[ixs]
        lst.indexoff = ixs
        lst.dirty = True

        self.indirect[lst.command] = (num_indexes, 1, ixs.start, vs.start, 0)

    def free(self, lst):
        """Remove a list from the array."""
        self.allocs.remove(lst)
        del self.indirect[lst.command]

        # Free space in allocators
        self.allocator.free(lst.vertoff)
        self.index_allocator.free(lst.indexoff)

        lst.buf = None
        lst.vertbuf = None
        lst.indexbuf = None

    def render(self):
        """Render all lists."""
        if not self.allocs:
            return

        dirty = False
        for a in self.allocs:
            if a.dirty:
                dirty = True
                a.dirty = False
        if dirty:
            self.vbo.write(self.verts)
            self.ibo.write(self.indexes)

        self.vao.render_indirect(
            self.indirect.get_buffer(),
            mode=self.mode,
        )
