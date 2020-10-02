import pytest
import asyncio

from wasabi2d import run, do
from wasabi2d import loop
from wasabi2d.clock import Clock


@pytest.fixture
def clock():
    """Return a new clock object."""
    return Clock()


async def run_clock(clock, *, frames, framerate=60):
    """A coroutine to step the clock forward a given number of frames."""
    for _ in range(frames):
        clock.tick(1 / framerate)
        await loop.next_tick()


teardown_function = setup_function = loop._clear_all


def test_schedule(clock):
    """We can schedule a coroutine."""
    v = None

    async def set_v(val):
        nonlocal v
        await clock.coro.sleep(0.1)
        v = val

    do(set_v(3))

    assert v is None
    run(run_clock(clock, frames=10))
    assert v == 3


def test_next_frame(clock):
    """We can await the very next frame."""
    dt = None

    async def frame_waiter():
        nonlocal dt
        dt = await clock.coro.next_frame()

    clock.coro.run(frame_waiter())
    assert dt is None
    run(run_clock(clock, frames=1))
    assert dt == 1 / 60


def test_await_frames(clock):
    """We can iterate over a sequence of frames."""
    ts = []

    async def multi_frame_waiter():
        async for t in clock.coro.frames(frames=3):
            ts.append(t)

    do(multi_frame_waiter())
    run(run_clock(clock, frames=3, framerate=10))

    assert ts == pytest.approx([0.1, 0.2, 0.3])


def test_await_seconds(clock):
    """We can iterate over a sequence of frames, in seconds."""
    ts = []

    async def multi_frame_waiter():
        async for t in clock.coro.frames(seconds=1.0):
            ts.append(t)

    do(multi_frame_waiter())
    run(run_clock(clock, frames=10, framerate=5))
    assert ts == pytest.approx([0.2, 0.4, 0.6, 0.8, 1.0])


def test_interpolate(clock):
    """We can interpolate a value over multiple frames."""
    vs = []

    async def interpolator():
        async for v in clock.coro.interpolate(1.0, 2.0, duration=0.5):
            vs.append(v)

    do(interpolator())
    run(run_clock(clock, frames=10, framerate=5))
    assert vs == pytest.approx([1.4, 1.8, 2.0])


def test_cancel(clock):
    """We can cancel a task."""
    ts = []

    async def multi_frame_waiter():
        try:
            async for t in clock.coro.frames():
                ts.append(t)
        except clock.coro.Cancelled:
            ts.append('cancelled')

    async def start_cancel():
        task = do(multi_frame_waiter())
        await loop.next_tick()  # Allow task to start and block on clock
        clock.tick(0.1)
        await loop.next_tick()  # Allow task to run one loop
        task.cancel()
        await loop.next_tick()  # Allow task to cancel

    run(start_cancel())
    assert ts == [0.1, 'cancelled']
