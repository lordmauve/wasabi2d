"""Sparse Vertex buffer with a packed index buffer."""
from typing import Dict, Tuple, ContextManager
from contextlib import contextmanager, nullcontext

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
            draw_context=nullcontext,
            capacity: int = 256,
            index_capacity: int = 512):
        self.mode = mode
        self.ctx = ctx
        self.prog = prog
        self.dtype = dtype_to_moderngl(dtype)
        self.allocs: Dict[int, Tuple[slice, np.ndarray]] = {}
        self.verts = MemoryBackedBuffer(ctx, capacity, dtype)
        self.indexes = IndexBuffer(ctx)
        self.dirty = False

    def insert(self, verts: np.ndarray, indexes: np.ndarray) -> int:
        """Allocate a list from within this buffer."""
        vs, vertbuf = self.verts.allocate(len(verts))
        id = self.indexes.insert(indexes + vs.start)

        vertbuf[:] = verts
        self.allocs[id] = vs, vertbuf
        self.dirty = True
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
        self.allocs[id] = vertoff, vertbuf
        self.dirty = True

    @contextmanager
    def get_verts(self, id: int) -> ContextManager[np.ndarray]:
        """Get the vertices for the given allocation.

        This is a context manager mainly to indicate that the calling code
        should not hold a reference to this array outside of the context.
        """
        self.dirty = True
        yield self.allocs[id][1]

    def remove(self, id: int):
        """Remove a list from the array."""
        vertoff, _ = self.allocs.pop(id)
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
