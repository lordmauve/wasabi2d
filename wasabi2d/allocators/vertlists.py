from typing import Sequence

import moderngl
import numpy as np

from .abstract import AbstractAllocator, NoCapacity


class Allocation:
    __slots__ = (
        'offset',
        'buf',
        'dirty',
    )

    def __init__(self, offset: int, dyn: np.ndarray, static: np.ndarray):
        self.offset = offset
        self.length = np.prod(dyn.shape)
        self.dyn = dyn
        self.static = static
        self.dyn_dirty = True
        self.static_dirty = True

    def free(self):
        raise NotImplementedError(
            "Cannot yet free a list allocation."
        )


class IndexAllocator:
    """Manage a buffer of vertex indexes, plus indirect render buffer."""

    def __init__(self, capacity=8192):
        self.allocator = AbstractAllocator(capacity)
        self.indexes = np.zeros(capacity, dtype='i4')
        self.allocs = []

    def allocate(self, indexes: Sequence[int], base_vertex: int):
        """Allocate the given indices into the buffer."""
        num = len(indexes)

        try:
            pos = self.allocator.alloc(num)
        except NoCapacity as e:
            new_capacity = e.recommended
            new_indexes = np.zeros(new_capacity, dtype='i4')
            new_indexes[:len(self.indexes)] = self.indexes
            self.indexes = new_indexes
            pos = self.allocator.alloc(num)

        self.indexes[pos] = indexes
        self.allocs.append(
            # (count, instanceCount, firstIndex, baseVertex, baseInstance)
            (num, 1, pos.start, base_vertex, 0),
        )


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


def dtype_to_moderngl(dtype: np.dtype):
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


class VertList:
    """Manage vertex lists within a buffer."""

    def __init__(
            self,
            ctx: moderngl.Context,
            dtype: np.dtype,
            capacity: int = 4096):
        self.ctx = ctx
        self.dtype = dtype
        self.capacity = capacity
        self._initialise()

    def _initialise(self):
        indices = np.array(indices, dtype='i4')
        alloc_length = alloc_length or (np.max(indices) + 1)

        self.allocated = len(self.sprites)

        # Allocate extra slots in the arrays for faster additions
        extra = max(32 - self.allocated, self.allocated // 2)

        for i, s in enumerate(self.sprites):
            s.array = self
            s.offset = i
            if s.verts is None:
                s._update()

        self.data = np.zeros(self.capacity, self.dtype)
        self.vbo = self.ctx.buffer(self.data, dynamic=True)
        self.ibuf = self.ctx.buffer(self.indexes)
        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo, '3f 4f', 'in_vert', 'in_color'),
                (self.uvbo, '2f', 'in_uv'),
            ],
            self.ibuf
        )

    def allocate(self, indices, alloc_length=0):
        indices = np.array(indices, dtype='i4')
        alloc_length = alloc_length or (np.max(indices) + 1)

    def add(self, s):
        """Add a sprite to the array.

        If there's unallocated space in the VBO we append the sprite.

        Otherwise we allocate new VBOs.
        """
        s.array = self
        if not s.verts:
            s._update()
        size = len(self.verts) // 4
        if self.allocated < size:
            i = self.allocated
            self.allocated += 1
            self.verts[i * 4:i * 4 + 4] = s.verts
            self.uvs[i * 4:i * 4 + 4] = s.uvs
            self.sprites.append(s)
            s.offset = i

            #TODO: We can send less data with write_chunks()
            self.vbo.write(self.verts)
            self.uvbo.write(self.uvs)
        else:
            self.sprites.append(s)
            self._allocate()

    def delete(self, s):
        """Remove a sprite from the array.

        To do this without resizing the buffer we move a sprite from the
        end of the array into the gap. This means that draw order changes.

        """
        assert s.array is self
        i = s.offset
        j = self.allocated - 1
        self.allocated -= 1
        if i == j:
            self.sprites.pop()
        else:
            moved = self.sprites[i] = self.sprites[j]
            self.sprites.pop()
            moved.offset = i
            self.verts[i * 4:i * 4 + 4] = self.verts[j * 4:j * 4 + 4]
            self.uvs[i * 4:i * 4 + 4] = self.uvs[j * 4:j * 4 + 4]
            # TODO: write only once per frame no matter how many adds/deletes
            self.vbo.write(self.verts)
            self.uvbo.write(self.uvs)
        s.array = None

    def render(self):
        """Render all sprites in the array."""
        self.prog['tex'].value = 0
        self.tex.use(0)
        dirty = False
        for i, s in enumerate(self.sprites):
            if s.verts is None:
                s._update()
                self.verts[i * 4:i * 4 + 4] = s.verts
                dirty = True
        assert self.verts.dtype == 'f4', \
            f"Dtype of verts is {self.verts.dtype}"
        if dirty:
            self.vbo.write(self.verts)
        self.vao.render(vertices=self.allocated * 6)

