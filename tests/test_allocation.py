import pytest

from wasabi2d.allocators.abstract import AbstractAllocator


@pytest.fixture
def alloc():
    """Fixture to return a new abstract allocator."""
    return AbstractAllocator(capacity=8192)


def test_allocate(alloc):
    """We can allocate a block of an arbitrary size."""
    assert alloc.alloc(5000) == slice(0, 5000)


def test_free(alloc):
    """We can free a block we allocated and recover all capacity."""
    block = alloc.alloc(5000)
    alloc.free(block)
    assert alloc.avail() == 8192


BLOCKS = [
    5,
    3000,
    256,
    256,
    1024,
    72,
]


def test_allocate_many(alloc):
    """We can allocate many blocks, such that they do not overlap."""
    slices = [alloc.alloc(sz) for sz in BLOCKS]
    for i, a in enumerate(slices):
        for b in slices[i + 1:]:
            assert a.stop <= b.start or b.stop <= a.start, \
                f"{a} overlaps with {b}"


def test_recover_many(alloc):
    """We can allocate and free many blocks."""
    allocations = [alloc.alloc(sz).start for sz in BLOCKS]
    for a in allocations[::-1]:
        alloc.free(a)
    assert alloc.avail() == 8192


def test_contiguous(alloc):
    """After allocating and freeing everything, space is contiguous."""
    allocations = [alloc.alloc(sz).start for sz in BLOCKS]
    for a in allocations[::-1]:
        alloc.free(a)
    assert list(alloc._free) == [(8192, 0)]
