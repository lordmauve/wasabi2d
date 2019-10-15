import pytest
import asyncio

from wasabi2d.clock import Clock


@pytest.fixture
def clock():
    """Return a new clock object."""
    return Clock()


def test_schedule(clock):
    """We can schedule a coroutine."""
    v = None

    async def set_v(val):
        nonlocal v
        await clock.coro.sleep(0.1)
        v = val

    clock.coro.run(set_v(3))
    assert v is None
    clock.tick(1)
    assert v == 3


def test_next_frame(clock):
    """We can await the very next frame."""
    dt = None

    async def frame_waiter():
        nonlocal dt
        dt = await clock.coro.next_frame()

    clock.coro.run(frame_waiter())
    assert dt is None
    clock.tick(0.125)
    assert dt == 0.125


def test_await_invalid(clock):
    """It is a TypeError to await an asyncio Future."""
    with pytest.raises(TypeError):
        clock.coro.run(asyncio.sleep(1))


def test_await_frames(clock):
    """We can iterate over a sequence of frames."""
    ts = []

    async def multi_frame_waiter():
        async for t in clock.coro.frames(frames=3):
            ts.append(t)

    clock.coro.run(multi_frame_waiter())
    for _ in range(10):
        clock.tick(0.1)

    assert ts == pytest.approx([0.1, 0.2, 0.3])


def test_await_seconds(clock):
    """We can iterate over a sequence of frames, in seconds."""
    ts = []

    async def multi_frame_waiter():
        async for t in clock.coro.frames(seconds=1.0):
            ts.append(t)

    clock.coro.run(multi_frame_waiter())
    for _ in range(10):
        clock.tick(0.2)

    assert ts == pytest.approx([0.2, 0.4, 0.6, 0.8, 1.0])


def test_interpolate(clock):
    """We can interpolate a value over multiple frames."""
    vs = []

    async def interpolator():
        async for v in clock.coro.interpolate(1.0, 2.0, duration=0.5):
            vs.append(v)

    clock.coro.run(interpolator())
    for _ in range(10):
        clock.tick(0.2)

    assert vs == pytest.approx([1.4, 1.8, 2.0])


def test_cancel(clock):
    """We can cancel a task."""
    ts = []

    async def multi_frame_waiter():
        try:
            async for t in clock.coro.frames(seconds=1.0):
                ts.append(t)
        except clock.coro.Cancelled:
            ts.append('cancelled')

    task = clock.coro.run(multi_frame_waiter())
    clock.tick(0.1)
    task.cancel()

    assert ts == [0.1, 'cancelled']
