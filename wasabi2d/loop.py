"""The event loop for Wasabi2D.

This is now based on coroutines and tasks but adapted to call synchronous
functions, for backwards compatibility.
"""
import time
from types import coroutine, CoroutineType
from typing import Optional
from functools import total_ordering
import heapq

import pygame.event
from . import clock


@coroutine
def _block(reschedule=False):
    """An awaitable that yields obj."""
    return (yield reschedule)


def resume_callback():
    """Get a callback to resume the current task.

    The callback can be called with an optional single argument which is the
    value that will be returned from the await.
    """
    return current_task._resume


async def next_tick() -> float:
    """Await the next tick.

    Return the amount of time that has passed in seconds (dt).
    """
    return (await _block(True))


class Cancelled(Exception):
    """An exception raised indicating a coroutine has been cancelled."""


def do(coro):
    """Schedule a task as runnable."""
    if isinstance(coro, CoroutineType):
        if coro.cr_running:
            raise RuntimeError(f"{coro!r} is already started")
    else:
        try:
            await_ = coro.__await__
        except AttributeError:
            raise RuntimeError(f"{coro!r} is not a coroutine or awaitable")
        coro = await_()

    task = Task(coro)
    task._resume()  # Start immediately, ie. this frame
    return task


@total_ordering
class Task:
    next_id = 0
    cancellable = True

    def __init__(self, coro):
        self.id = Task.next_id
        Task.next_id += 1

        self._scheduled = False
        self.coro = coro
        self.finished = False
        self.result = None
        self.cancelled = False  # Have we been cancelled?
        self.joiners = set()  # Other tasks waiting for this one
        self._resume_value = None  # The next value to send to the task

    def __repr__(self):
        return f"Task({self.coro!r})"

    def __lt__(self, other):
        return self.next_id < other.next_id

    def _step(self):
        global current_task
        assert not self.finished, \
            f"{self!r} was rescheduled when already finished"
        self._scheduled = False
        if self.cancelled:
            try:
                current_task = self
                self.coro.throw(Cancelled())
            except Cancelled:
                pass
            except StopIteration as e:
                self.result = e.value
            else:
                import warnings
                warnings.warn(
                    ResourceWarning,
                    f"Coroutine {self.coro} failed to stop when cancelled"
                )
            finally:
                current_task = None
                self._finish()
        else:
            try:
                current_task = self
                v, self._resume_value = self._resume_value, None
                result = self.coro.send(v)
            except StopIteration as e:
                self.result = e.value
                self._finish()
            except Exception:
                self._finish()
                raise
            else:
                if result:
                    self._park()
            finally:
                current_task = None

    def _park(self):
        """Block until the next frame."""
        assert not self.finished
        if not self._scheduled:
            heapq.heappush(runnable_next, self)
            self._scheduled = True

    def _resume(self, v=None):
        assert not self.finished
        if not self._scheduled:
            heapq.heappush(runnable, self)
            self._resume_value = v
            self._scheduled = True

    def _finish(self):
        self.finished = True
        for task in self.joiners:
            task._resume(self.result)
        self.joiners.clear()

    def cancel(self):
        """Cancel this task."""
        assert self.cancellable
        if self.finished or self.cancelled:
            return
        self.cancelled = True
        self._resume()

    async def join(self):
        """Wait until this task completes."""
        if self.finished:
            return self.result
        try:
            self.joiners.add(current_task)
            return (await _block())
        except Cancelled:
            self.joiners.discard(current_task)
            raise


runnable = []
runnable_next = []

#: This is the currently executing task, if any.
current_task: Optional[Task] = None


class PygameEvents:
    def __init__(self, evmapper, get_events=pygame.event.get):
        self.evmapper = evmapper
        self.get_events = get_events
        self.waiters = {}

    async def wait(self, *event_types):
        handler = current_task._resume

        for event_type in event_types:
            if event_type in self.waiters:
                self.waiters[event_type].add(handler)
            else:
                self.waiters[event_type] = {handler}

        try:
            await _block()
        except Cancelled:
            for event_type in event_types:
                self._waiter[event_type].discard(handler)
            raise

    async def run(self):
        from .game import UpdateEvent, DrawEvent
        from .clock import default_clock
        t = dt = 0.0
        updated = True
        while True:
            events = self.get_events()
            update = UpdateEvent(UpdateEvent, t, dt, None)

            # Because the current draw strategy a single draw is
            # only flipped at the next draw. Therefore we must always issue
            # a draw event. However we pass the "updated" flag and hope the
            # renderer can deal with this.

            draw = DrawEvent(DrawEvent, t, dt, updated)
            events.extend([update, draw])

            updated = False
            for event in events:
                updated |= self.evmapper.dispatch_event(event)
                handlers = self.waiters.get(event.type, ())
                for h in handlers:
                    h(event)
                if handlers:
                    updated = True

            updated |= default_clock.tick(dt)

            dt = await next_tick()
            t += dt


async def frames_dt():
    """Iterate over frames."""
    while True:
        yield (await next_tick())


async def gather(*coros):
    """Wait for all of the given coroutines/tasks to finish."""
    tasks = []
    for coro in coros:
        tasks.append(do(coro))
    for t in tasks:
        await t.join()


class Nursery:
    """A group of coroutines."""

    def __init__(self):
        self.tasks = set()

    def do(self, coro):
        task = do(coro)
        self.tasks.add(task)
        return task

    def cancel(self):
        for t in self.tasks:
            t.cancel()
        self.tasks.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, cls, inst, tb):
        if cls:
            return self.cancel()

        try:
            while self.tasks:
                t = self.tasks.pop()
                await t.join()
        except Cancelled:
            t.cancel()
            for t in self.tasks:
                t.cancel()
            self.tasks = None


# Override timing calculation when recording video
lock_fps = False


def run(main=None, timefunc=time.perf_counter):
    """Run the event loop."""
    global current_task, runnable, runnable_next
    if main:
        main = do(main)

    t = timefunc()
    while True:
        if main and main.finished:
            return main.result
        while runnable:
            task = heapq.heappop(runnable)
            task._step()

        now = timefunc()
        if lock_fps:
            dt = 1.0 / 60.0
        else:
            dt = now - t
        t = now

        for task in runnable_next:
            task._resume_value = dt
        runnable, runnable_next = runnable_next, runnable


def _clear_all():
    """Clear all tasks. For use in testing only."""
    for task in runnable + runnable_next:
        # Cancel them in case they get rescheduled somehow
        task.cancelled = True
    runnable.clear()
    runnable_next.clear()
