from typing import Sequence

from numpy import np
from sortedcontainers import SortedList


class Allocation:
    __slots__ = (
        'offset',
        'dyn',
        'static',
        'dyn_dirty',
        'static_dirty',
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


class AbstractAllocator:
    """Manage allocations within a block of items."""

    def __init__(self, capacity=8192):
        self.indexes = np.zeros(capacity, dtype='i4')

        self.allocs = []
        self.indirect_capacity = 50

        self._free = SortedList([(capacity, 0)])

    @property
    def capacity(self):
        """Get the capacity of the buffer."""
        return len(self.indexes)

    def _release(self, offset, length):
        if not length:
            return
        # TODO: merge with previous if possible
        # TODO: split in powers of two to avoid fragmentation
        self._free.append((length, offset))

    def allocate(self, indexes: Sequence[int], base_vertex: int):
        """Allocate the given indices into the buffer."""
        dirty = False
        num = len(indexes)
        pos = self._free.bisect_left((num, 0))
        if pos == len(self._free):
            # capacity is not high enough
            capacity = len(self.indexes)
            new_capacity = 2048
            while new_capacity < num:
                new_capacity *= 2
            self.indexes = np.hstack([
                self.indexes,
                [0] * new_capacity
            ]).astype('i4')
            self._release(capacity, new_capacity)
            dirty = True

            pos = self._free.bisect_left((num, 0))

        block_size, offset = self._free.pop(pos)

        # Release the rest of the block in power-of-2 blocks
        mid = block_size // 2
        while mid > num:
            self._release(offset + mid, block_size - mid)
            block_size = mid
            mid = block_size // 2

        end_off = offset + num
        self.indexes[offset:end_off] = indexes
        self.allocs.append(
            # (count, instanceCount, firstIndex, baseVertex, baseInstance)
            (num, 1, offset, base_vertex, 0),
        )

        # Release the remainder of the block
        self._release(end_off, block_size - num)

        if dirty:
            return 0, self.capacity
        return offset, num


class IndexAllocator:
    """Manage a buffer of vertex indexes, plus indirect render buffer."""

    def __init__(self, capacity=8192):
        self.indexes = np.zeros(capacity, dtype='i4')

        self.allocs = []
        self.indirect_capacity = 50

        self._free = SortedList([(capacity, 0)])

    @property
    def capacity(self):
        """Get the capacity of the buffer."""
        return len(self.indexes)

    def _release(self, offset, length):
        if not length:
            return
        # TODO: merge with previous if possible
        # TODO: split in powers of two to avoid fragmentation
        self._free.append((length, offset))

    def allocate(self, indexes: Sequence[int], base_vertex: int):
        """Allocate the given indices into the buffer."""
        dirty = False
        num = len(indexes)
        pos = self._free.bisect_left((num, 0))
        if pos == len(self._free):
            # capacity is not high enough
            capacity = len(self.indexes)
            new_capacity = 2048
            while new_capacity < num:
                new_capacity *= 2
            self.indexes = np.hstack([
                self.indexes,
                [0] * new_capacity
            ]).astype('i4')
            self._release(capacity, new_capacity)
            dirty = True

            pos = self._free.bisect_left((num, 0))

        block_size, offset = self._free.pop(pos)

        # Release the rest of the block in power-of-2 blocks
        mid = block_size // 2
        while mid > num:
            self._release(offset + mid, block_size - mid)
            block_size = mid
            mid = block_size // 2

        end_off = offset + num
        self.indexes[offset:end_off] = indexes
        self.allocs.append(
            # (count, instanceCount, firstIndex, baseVertex, baseInstance)
            (num, 1, offset, base_vertex, 0),
        )

        # Release the remainder of the block
        self._release(end_off, block_size - num)

        if dirty:
            return 0, self.capacity
        return offset, num


class VertList:
    """Manage vertex lists within a buffer."""
    QUAD = np.array([0, 1, 2, 0, 2, 3], dtype='i4')

    def __init__(self, ctx, dyn_vals, static_vals=0, capacity=4096):
        self.ctx = ctx
        self.dyn_vals = dyn_vals
        self.static_vals = static_vals

        self._free = SortedList([(4096, 0)])
        self.allocations = []
        self._capacity = 4096
        self._initialise()

    def _initialise(self, indices, alloc_length=0):
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

        self.indexes = np.vstack([
            self.QUAD + 4 * i
            for i in range(self.allocated + extra)
        ])
        self.uvs = np.vstack(
            [s.uvs for s in self.sprites]
            + [np.zeros((4 * extra, 2), dtype='f4')]
        )
        self.verts = np.vstack(
            [s.verts for s in self.sprites]
            + [np.zeros((4 * extra, 7), dtype='f4')]
        )

        self.vbo = self.ctx.buffer(self.verts, dynamic=True)
        self.uvbo = self.ctx.buffer(self.uvs)
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

