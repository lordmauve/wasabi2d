"""Tests for the IndexBuffer class.

Here we test allocation and deallocation, but not uploading to the GL.

"""
from typing import List
import pytest
from unittest.mock import Mock

import numpy as np

from wasabi2d.allocators.index import IndexBuffer, merge_seq


def callablefixture(func):
    """Fuck off, pytest."""
    f = pytest.fixture(func)
    copy_attrs = ['__pytest_wrapped__', '_pytestfixturefunction']
    for a in copy_attrs:
        setattr(func, a, getattr(f, a))
    return func


@callablefixture
def idxbuf() -> IndexBuffer:
    """Fixture to return an IndexBuffer with a mock context."""
    return IndexBuffer(Mock())


@pytest.fixture
def indexes() -> np.ndarray:
    """Fixture to return valid indices."""
    return np.arange(0, 2, dtype='uint32')


def test_insert(idxbuf, indexes):
    """We can insert indices into the buffer."""
    id = idxbuf.insert(indexes)
    assert id == 0
    assert np.all(idxbuf.as_array() == indexes)
    assert idxbuf.dirty


def test_remove(idxbuf, indexes):
    """We can remove previously inserted indexes."""
    id = idxbuf.insert(indexes)
    idxbuf.dirty = False

    idxbuf.remove(id)
    assert id not in idxbuf
    assert not idxbuf
    assert idxbuf.dirty


def test_concat(idxbuf, indexes):
    """We can insert two sets of indices and concatenate them."""
    id = idxbuf.insert(indexes)
    id2 = idxbuf.insert(indexes + 2)
    assert [id, id2] == [0, 1]
    assert np.all(idxbuf.as_array() == np.array([0, 1, 2, 3]))


def test_sort(idxbuf, indexes):
    """We can insert indices with a sort key."""
    idxbuf.insert(indexes, 1)
    idxbuf.insert(indexes + 2, -1)
    idxbuf.insert(indexes + 4, 0)
    assert np.all(idxbuf.as_array() == np.array([2, 3, 4, 5, 0, 1]))


def test_update_indexes(idxbuf, indexes):
    """We can update the values of an allocation, including its length."""
    id = idxbuf.insert(indexes)
    idxbuf.dirty = False

    idxbuf.set_indexes(id, np.ones(4, dtype=np.uint32))
    assert np.all(idxbuf.as_array() == [1, 1, 1, 1])
    assert idxbuf.dirty


def test_update_sort(idxbuf, indexes):
    """We can update the sort key of an allocation."""
    id = idxbuf.insert(indexes, 1)
    idxbuf.insert(indexes + 2, -1)
    idxbuf.insert(indexes + 4, 0)
    idxbuf.dirty = False

    idxbuf.set_sort(id, -2)
    assert np.all(idxbuf.as_array() == np.array([0, 1, 2, 3, 4, 5]))
    assert idxbuf.dirty


def test_update_sort_and_indexes(idxbuf, indexes):
    """We can update the sort key of an allocation."""
    id = idxbuf.insert(indexes, 1)
    idxbuf.insert(indexes + 2, -1)
    idxbuf.insert(indexes + 4, 0)
    idxbuf.dirty = False

    idxbuf.update(id, np.ones(3, dtype=np.uint32), -2)
    assert np.all(idxbuf.as_array() == np.array([1, 1, 1, 2, 3, 4, 5]))
    assert idxbuf.dirty


def test_clear(idxbuf, indexes):
    """We can insert two sets of indices and concatenate them."""
    id1 = idxbuf.insert(indexes)
    idxbuf.insert(indexes)
    idxbuf.dirty = False

    idxbuf.clear()
    assert not idxbuf
    assert id1 not in idxbuf
    assert idxbuf.dirty


def indexarray(v: List[int]) -> np.ndarray:
    """Create an array of one index."""
    return np.array(v, dtype=np.uint32)


def test_merge():
    """We can merge together buffers."""
    bufa, bufb = idxbuf(), idxbuf()
    bufa.insert(indexarray([1]), 1)
    bufa.insert(indexarray([2, 3]), 2)
    bufb.insert(indexarray([5, 6]), 5)
    bufb.insert(indexarray([20]), 20)
    bufa.insert(indexarray([10]), 10)
    bufa.insert(indexarray([11]), 11)

    merged = merge_seq([bufa, bufb])
    diffable = [
        ('bufa' if b is bufa else 'bufb', start, stop)
        for b, start, stop in merged
    ]
    assert diffable == [
        ('bufa', 0, 3),
        ('bufb', 0, 2),
        ('bufa', 3, 5),
        ('bufb', 2, 3),
    ]
