from typing import Union

from sortedcontainers import SortedList


class NoCapacity(Exception):
    """Raised when the allocator is out of capacity to allocate a block.

    The attribute `.recommended` will contain a recommended size to grow to.
    """


class AbstractAllocator:
    """Manage allocations within a block of items.

    This is abstract because we don't actually assume anything about the types
    of the items or how to write to them.

    """

    def __init__(self, capacity: int = 8192):
        self.capacity = capacity
        self.allocs = {}
        self._free = SortedList([(capacity, 0)])

    def avail(self) -> int:
        """Get the current available capacity."""
        return sum(cap for cap, off in self._free)

    def grow(self, new_capacity: int):
        """Grow the available space for allocation to new_capacity.

        No reallocations or compactions are done here so the only guaranteed
        contiguous new free space is at the end.
        """
        self._release(self.capacity, new_capacity - self.capacity)
        self.capacity = new_capacity

    def _release(self, offset, length):
        """Release the given block back to the pool.

        We consider joining this block to a subsequent one. We don't currently
        consider joining it to the previous block.

        """
        if not length:
            return

        while True:
            k = (length, offset)
            idx = self._free.bisect_left(k)
            if idx >= len(self._free):
                self._free.add(k)
                return

            next_length, next_off = self._free[idx]
            if next_off != (length + offset):
                return

            self._free.pop(idx)
            length += next_length

    def alloc(self, num: int) -> slice:
        """Allocate a block of size num.

        Return a slice, or raise NoCapacity if there was insufficient
        capacity available.

        """
        pos = self._free.bisect_left((num, 0))
        if pos == len(self._free):
            # capacity is not high enough
            new_capacity = self.capacity
            while new_capacity < num:
                new_capacity *= 2

            err = NoCapacity()
            err.recommended = self.capacity + new_capacity
            raise err

        block_size, offset = self._free.pop(pos)

        # Release the rest of the block in power-of-2 blocks
        mid = block_size // 2
        while mid >= num >= 2:
            self._release(offset + mid, block_size - mid)
            block_size = mid
            mid = block_size // 2

        end_off = offset + num

        self._release(end_off, block_size - num)

        # Store the size of the block that we allocated
        self.allocs[offset] = num
        return slice(offset, end_off)

    def free(self, offset: Union[int, slice]):
        """Free the block at offset."""
        if isinstance(offset, slice):
            offset = offset.start
        try:
            size = self.allocs.pop(offset)
        except KeyError:
            raise KeyError(f"Offset {offset} is not allocated.") from None
        self._release(offset, size)
