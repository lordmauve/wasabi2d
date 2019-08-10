from sortedcontainers import SortedList

# Set of powers of two
POTWO = {2 ** n for n in range(32)}
is_power_of_two = POTWO.__contains__


class NoCapacity(Exception):
    """Raised when the allocator is out of capacity to allocate a block.

    The attribute `.recommended` will contain a recommended size to grow to.
    """


class AbstractAllocator:
    """Manage allocations within a block of items."""

    def __init__(self, capacity=8192):
        self.capacity = capacity
        self.allocs = {}
        self._free = SortedList([(capacity, 0)])

    def avail(self) -> int:
        """Get the current available capacity."""
        return sum(cap for cap, off in self._free)

    def grow(self, new_capacity):
        """Grow the available space for allocation to new_capacity."""
        self._release(self.capacity, new_capacity - self.capacity)
        self.capacity = new_capacity

    def _release(self, offset, length):
        if not length:
            return

        k = (length, offset)
        idx = self._free.bisect_left(k)
        if idx >= len(self._free):
            self._free.add(k)
            return

        next_length, next_off = self._free[idx]
        if next_off == (length + offset):
            self._free.pop(idx)
        self._release(offset, length + next_length)

    def alloc(self, num: int) -> slice:
        """Allocate a block of size num.

        Return a slice, or raise NoCapacity if there was insufficient
        capacity available.

        """
        pos = self._free.bisect_left((num, 0))
        if pos == len(self._free):
            # capacity is not high enough
            new_capacity = 2048
            while new_capacity < num:
                new_capacity *= 2

            err = NoCapacity()
            err.recommended = self.capacity + new_capacity
            raise err

        block_size, offset = self._free.pop(pos)

        # Release the rest of the block in power-of-2 blocks
        mid = block_size // 2
        while mid > num:
            self._release(offset + mid, block_size - mid)
            block_size = mid
            mid = block_size // 2

        end_off = offset + num

        self._release(end_off, block_size - num)

        # Store the size of the block that we allocated
        self.allocs[offset] = num
        return slice(offset, end_off)

    def free(self, offset):
        """Free the block at offset."""
        if isinstance(offset, slice):
            offset = offset.start
        try:
            size = self.allocs.pop(offset)
        except IndexError:
            raise IndexError(f"Offset {offset} is not allocated.")
        self._release(offset, size)
