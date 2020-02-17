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

    def __init__(self, ctx: mgl.Context):
        self.buffer = None
        self.ctx = ctx

        # Keep sort keys in a separate mapping
        self.sort_keys: Dict[int, Any] = {}
        self.allocations = SortedDict(self._sort_key)

        # Track whether we have updates
        self.dirty: bool = True

        # We allocate identifiers for each allocation. These are sequential
        # and form part of the sort key; this ensures that insertion order
        # can be preserved.
        self.next_id: int = 0

    def _sort_key(self, id: int) -> Tuple[Any, int]:
        """Get a sort key for the given index."""
        return self.sort_keys.get(id), id

    def insert(self, indexes: np.ndarray, sort: Any = None) -> int:
        """Add indexes to the buffer."""
        assert indexes.dtype == np.uint32, \
            f"incorrect dtype {indexes.dtype!r}, expected uint32"
        id = self.next_id
        self.next_id += 1

        self.sort_keys[id] = sort
        self.allocations[id] = indexes
        self.dirty = True
        return id

    def remove(self, id: int):
        """Remove an index range."""
        del self.sort_keys[id]
        del self.allocations[id]
        self.dirty = True

    def clear(self):
        """Clear all allocations."""
        self.allocations.clear()
        self.sort_keys.clear()
        self.next_id = 0
        self.dirty = True

    def __contains__(self, id: int) -> bool:
        """Return True if the given id is allocated."""
        return id in self.allocations

    def __bool__(self) -> bool:
        return bool(self.allocations)

    def set_indexes(self, id: int, indexes: np.ndarray):
        """Replace the indexes for an allocation."""
        assert indexes.dtype == np.uint32, \
            f"incorrect dtype {indexes.dtype!r}, expected uint32"
        self.allocations[id] = indexes
        self.dirty = True

    def set_sort(self, id: int, sort: Any):
        """Set the sort key for an allocation."""
        indexes = self.allocations.pop(id)
        self.sort_keys[id] = sort
        self.allocations[id] = indexes
        self.dirty = True

    def update(self, id: int, indexes: np.ndarray, sort: Any = None):
        """Update sort and indexes for an allocation."""
        assert indexes.dtype == np.uint32, \
            f"incorrect dtype {indexes.dtype!r}, expected uint32"
        del self.allocations[id]
        self.sort_keys[id] = sort
        self.allocations[id] = indexes
        self.dirty = True

    def as_array(self) -> np.ndarray:
        """Flatten the allocations to a numpy array."""
        return np.hstack(self.allocations.values())

    def get_buffer(self) -> mgl.Buffer:
        """Get the index buffer."""
        if self.dirty:
            if self.buffer:
                # TODO: use moderngl orphan with resize
                self.buffer.release()
            self.buffer = self.ctx.buffer(self.as_array(), dtype='u4')
        return self.buffer

    def release(self):
        """Release the buffer, if allocated."""
        if self.buffer:
            self.buffer.release()
            self.buffer = None
            self.dirty = True

    __del__ = release
