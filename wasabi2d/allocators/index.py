"""Allocator for index buffers.

Without indirect rendering (unavailable on Mac OS X) we have to rely on packed
index buffers with primitive restarts where necessary. This requires rebuilding
the index buffer itself when anything changes, which is likely to be more
expensive than just rebuilding the indirect buffer.

Users must insert their own primitive restart commands.

These buffers support sorting of the allocations, which can be used to
implement depth-sorted or y-sorted layers.

"""
from typing import Any, Dict, Tuple

import numpy as np
import moderngl as mgl
from sortedcontainers import SortedDict


class IndexBuffer:
    """Abstraction over index lists.

    We use integer identifiers to track the allocations. This allows
    encapsulating modifications; returning a reference would not.

    """

    def __init__(self, ctx: mgl.Context, capacity: int = 1024):
        self.ctx = ctx
        self.capacity = capacity

        # Keep sort keys in a separate mapping
        self.sort_keys: Dict[int, Any] = {}
        self.allocations = SortedDict(key=self._sort_key)

        # Track whether we have updates
        self.dirty: bool = True

        # We allocate identifiers for each allocation. These are sequential
        # and form part of the sort key; this ensures that insertion order
        # can be preserved.
        self.next_id: int = 0
        self.id_map: Dict[int, list] = {}

    def _sort_key(self, id: int) -> Tuple[Any, int]:
        """Get a sort key for the given index."""
        return self.sort_keys.get(id), id

    def add(self, indexes: np.ndarray, sort: Any = None) -> int:
        """Add indexes to the buffer."""
        assert indexes.dtype is np.uint32, f"invalid dtype {indexes.dtype!r}"
        id = self.next_id
        self.next_id += 1

        self.sort_keys[id] = sort
        self.allocations[id] = indexes
        self.dirty = True

    def remove(self, id: int):
        del self.sort_keys[id]
        del self.allocations[id]

    def set_indexes(self, id: int, indexes: np.ndarray):
        """Replace the indexes for an allocation."""
        assert indexes.dtype is np.uint32, f"invalid dtype {indexes.dtype!r}"
        self.allocations[id] = indexes
        self.dirty = True

    def set_sort(self, id: int, sort: Any):
        """Set the sort key for an allocation."""
        indexes = self.allocations.pop(id)
        self.sort_keys[id] = sort
        self.allocations[id] = indexes

    def update(self, id: int, indexes: np.ndarray, sort: Any = None):
        """Update sort and indexes for an allocation."""
        assert indexes.dtype is np.uint32, f"invalid dtype {indexes.dtype!r}"
        del self.allocations[id]
        self.sort_keys[id] = sort
        self.allocations[id] = indexes

    def get_buffer(self) -> mgl.Buffer:
        """Get the index buffer."""
        if self.dirty:
            if self.buffer:
                self.buffer.release()
            data = np.hstack(self.allocations.values())
            self.buffer = self.ctx.buffer(data, dtype='u4')
        return self.buffer

    def release(self):
        """Release the buffer, if allocated."""
        if self.buffer:
            self.buffer.release()
            self.buffer = None

    __del__ = release
