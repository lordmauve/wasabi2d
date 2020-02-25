"""Sparse Vertex buffer with a packed index buffer."""
from typing import Dict, Tuple, ContextManager
from contextlib import nullcontext

import moderngl
import numpy as np

from .index import IndexBuffer
from .vertlists import dtype_to_moderngl, MemoryBackedBuffer


class PackedBuffer:
    def __init__(
            self,
            mode: int,
            ctx: moderngl.Context,
            prog: moderngl.Program,
            dtype: np.dtype,
            draw_context: ContextManager = nullcontext(),
            capacity: int = 256,
            index_capacity: int = 512):
        self.mode = mode
        self.ctx = ctx
        self.prog = prog
        self.dtype = dtype_to_moderngl(dtype)
        self.allocs: Dict[int, Tuple[slice, np.ndarray]] = {}
        self.verts = MemoryBackedBuffer(ctx, capacity, dtype)
        self.indexes = IndexBuffer(ctx)
        self.draw_context = draw_context
        self.dirty = False

    def empty(self) -> bool:
        """Return True if there are no allocations in this buffer."""
        return bool(self.allocs)

    def alloc(
        self,
        num_verts: int,
        indexes: np.ndarray
    ) -> Tuple[int, np.ndarray]:
        """Allocate a list from within this buffer.

        Return the allocated ID and an array view that can be used to set
        the vertex data immediately.

        The array view is not guaranteed to be valid after other array
        update operations.

        """
        vertoff, vertbuf = self.verts.allocate(num_verts)
        id = self.indexes.insert(indexes + vertoff.start)

        self.allocs[id] = vertoff
        self.dirty = True
        return id, vertbuf

    def insert(self, verts: np.ndarray, indexes: np.ndarray) -> int:
        """Allocate a list from within this buffer."""
        id, vertbuf = self.alloc(len(verts), indexes)
        vertbuf[:] = verts
        return id

    def realloc(self, id: int, verts: np.ndarray, indexes: np.ndarray):
        """Update an allocation."""
        vertoff, _ = self.allocs.pop(id)

        vertoff, vertbuf = self.verts.realloc(
            vertoff,
            len(verts),
        )
        vertbuf[:] = verts
        self.indexes.set_indexes(id, indexes + vertoff.start)
        self.allocs[id] = vertoff
        self.dirty = True

    def get_verts(self, id: int) -> np.ndarray:
        """Get the vertex slice for the given allocation.

        It is assumed that the vertices will be modified and need to be
        synced to the GL.

        It is not guaranteed that the slice will remain valid after other
        array update operations.

        """
        self.dirty = True
        vertoff = self.allocs[id]
        return self.verts.array[vertoff]

    def remove(self, id: int):
        """Remove a list from the array."""
        vertoff = self.allocs.pop(id)
        self.verts.free(vertoff)
        self.indexes.remove(id)
        self.dirty = True

    def get_vao(self):
        # TODO: use the dirty list to more accurately indicate which parts of
        # a buffer need updating.
        vbo = self.verts.get_buffer(self.dirty)
        ibo = self.indexes.get_buffer()

        # TODO: only recreate the VAO if buffers have changed
        vao = self.ctx.vertex_array(
            self.prog,
            [
                (vbo, *self.dtype),
            ],
            ibo
        )
        return vao

    def render(self, camera):
        """Render all lists."""
        if not self.allocs:
            return
        vao = self.get_vao()
        with self.draw_context:
            vao.render(self.mode)
        vao.release()

    def release(self):
        """Release this array."""
        self.verts.release()
        self.indexes.release()
