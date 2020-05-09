"""Allocator for index buffers.

Without indirect rendering (unavailable on Mac OS X) we have to rely on packed
index buffers with primitive restarts where necessary. This requires rebuilding
the index buffer itself when anything changes, which is likely to be more
expensive than just rebuilding the indirect buffer.

Users must insert their own primitive restart commands.

These buffers support sorting of the allocations, which can be used to
implement depth-sorted or y-sorted layers.

"""
from typing import Any, Dict, Tuple, Iterable, Sequence, Mapping
import heapq
from functools import total_ordering

import numpy as np
import moderngl as mgl
from sortedcontainers import SortedDict


class IndexBuffer:
    """Abstraction over index lists.

    We use integer identifiers to track the allocations, for encapsulation.
    These are generated anyway as a way to preserve insertion order in the
    absence of any other sort key.

    """

    def __init__(self, ctx: mgl.Context):
        self.buffer = None
        self.ctx = ctx

        # Allocation id to sort key
        self.id_lookup: Dict[int, Tuple[Any, int]] = {}

        # Sorted list of sort keys to index arrays
        self.allocations: Mapping[Tuple[Any, int], np.ndarray] = SortedDict()

        # Track whether we have updates
        self.dirty: bool = True

        # We allocate identifiers for each allocation. These are sequential
        # and form part of the sort key; this ensures that insertion order
        # can be preserved.
        self.next_id: int = 1  # start at 1 so we can test bool(id)

    def insert(self, indexes: np.ndarray, sort: Any = None) -> int:
        """Add indexes to the buffer."""
        assert indexes.dtype == np.uint32, \
            f"incorrect dtype {indexes.dtype!r}, expected uint32"
        id = self.next_id
        self.next_id += 1

        indexes.flags.writeable = False
        k = sort, id
        self.id_lookup[id] = k
        self.allocations[k] = indexes
        self.dirty = True
        return id

    def remove(self, id: int):
        """Remove an index range."""
        k = self.id_lookup.pop(id)
        del self.allocations[k]
        self.dirty = True

    def clear(self):
        """Clear all allocations."""
        self.allocations.clear()
        self.id_lookup.clear()
        self.next_id = 0
        self.dirty = True

    def __contains__(self, id: int) -> bool:
        """Return True if the given id is allocated."""
        return id in self.id_lookup

    def __bool__(self) -> bool:
        return bool(self.id_lookup)

    def set_indexes(self, id: int, indexes: np.ndarray):
        """Replace the indexes for an allocation."""
        assert indexes.dtype == np.uint32, \
            f"incorrect dtype {indexes.dtype!r}, expected uint32"
        indexes.flags.writeable = False
        k = self.id_lookup[id]
        self.allocations[k] = indexes
        self.dirty = True

    def set_sort(self, id: int, sort: Any):
        """Set the sort key for an allocation."""
        k = self.id_lookup[id]
        indexes = self.allocations.pop(k)
        k = sort, id
        self.id_lookup[id] = k
        self.allocations[k] = indexes
        self.dirty = True

    def update(self, id: int, indexes: np.ndarray, sort: Any = None):
        """Update sort and indexes for an allocation."""
        assert indexes.dtype == np.uint32, \
            f"incorrect dtype {indexes.dtype!r}, expected uint32"
        indexes.flags.writeable = False
        k = self.id_lookup.pop(id)
        del self.allocations[k]

        k = sort, id
        self.id_lookup[id] = k
        self.allocations[k] = indexes
        self.dirty = True

    def as_array(self) -> np.ndarray:
        """Flatten the allocations to a numpy array."""
        # TODO: maybe track the total length of the allocations and keep a
        # memoized array here. This would let us hstack into an existing array
        # if our allocations have simply changed sort key.
        return np.hstack(self.allocations.values())

    def get_buffer(self) -> mgl.Buffer:
        """Get the index buffer."""
        if self.dirty:
            if self.buffer:
                # TODO: use moderngl orphan with resize
                self.buffer.release()
            self.buffer = self.ctx.buffer(self.as_array())
        return self.buffer

    def release(self):
        """Release the buffer, if allocated."""
        if self.buffer:
            self.buffer.release()
            self.buffer = None
            self.dirty = True

    __del__ = release


@total_ordering
class BufIter:
    """An iterator for the merge."""
    __slots__ = ('it', 'peeked', 'idxs', 'idxpos')

    def __init__(self, buffer: IndexBuffer):
        self.it = iter(buffer.allocations.items())
        self.peeked, self.idxs = next(self.it)
        self.idxpos = 0

    def next(self):
        item = self.peeked, self.idxs
        self.idxpos += len(self.idxs)
        self.peeked, self.idxs = next(self.it, None)
        return item

    def __lt__(self, other):
        return self.peeked < other.peeked

    def __eq__(self, other):
        return self.peeked == other.peeked


def bufiter(buf: IndexBuffer) -> Iterable[Tuple[Any, IndexBuffer, int, int]]:
    """Iterate over allocations in a buffer."""
    pos = 0
    for (sort, id), indexes in buf.allocations.items():
        nextpos = pos + len(indexes)
        yield sort, buf, pos, nextpos
        pos = nextpos


def merge_seq(
    buffers: Sequence[IndexBuffer]
) -> Iterable[Tuple[IndexBuffer, int, int]]:
    """Merge a set of index buffers sorted by a common sort key.

    Yield contiguous groups of indexes.

    This implementation is O(n) in the number of allocations. We could do
    better - closer to O(m log n) for n allocations and m switches - if we
    had cached offsets for each index range. Then we could bisect into a
    buffer and read out the offset. This would still be an optimisation if we
    can avoid rebuilding that cache every frame. This is true if primitives
    do not move.

    """
    bufiters = map(bufiter, buffers)
    merged_allocs = heapq.merge(*bufiters, key=lambda i: (i[0], id(i[1])))
    try:
        _, lastbuf, laststart, lastend = next(merged_allocs)
    except StopIteration:
        return
    for _, buf, start, end in merged_allocs:
        if buf is not lastbuf:
            yield lastbuf, laststart, lastend
            lastbuf = buf
            laststart = start
            lastend = end
        else:
            lastend = end
    yield lastbuf, laststart, lastend
