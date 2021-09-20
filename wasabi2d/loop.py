"""The event loop for Wasabi2D.

This is now based on coroutines and tasks but adapted to call synchronous
functions, for backwards compatibility.
"""
import time
import types
from typing import Optional
from functools import total_ordering
import heapq

import pygame.event


@types.coroutine
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
    if isinstance(coro, types.CoroutineType):
        if coro.cr_running:
            raise RuntimeError(f"{coro!r} is already started")
    else:
        try:
            await_ = coro.__await__
        except AttributeError:
            if isinstance(coro, types.FunctionType):
                raise RuntimeError(
                    f"{coro.__qualname__} is a function object; "
                    "did you forget to call it?"
                ) from None
            raise RuntimeError(
                f"{coro!r} is not a coroutine or awaitable"
            ) from None
        coro = await_()

    task = Task(coro)
    task._resume()  # Start immediately, ie. this frame
    return task


class Event(set):
    """A concurrency primitive where many tasks can wait for one event.

    Events start in an "un-set" state. In this state a task waiting for the
    event will block. Calling .set() will release all tasks, and subsequent
    waits will not block.

    """
    __slots__ = ('_is_set')

    def __init__(self):
        """Construct an event. Events are initially in the un-set state."""
        self._is_set = False

    def __bool__(self):
        """Return True if the event is set."""
        return self._is_set

    is_set = __bool__

    def set(self):
        """Set the event.

        This will release all blocked tasks. Subsequent waits will not block.
        """
        for waiter in self:
            waiter()
        self.clear()

    def reset(self):
        """Reset the event.

        Subsequent waits will block until the event is set again.
        """
        self._is_set = False

    def __await__(self):
        """Await this event object."""
        if self._is_set:
            return
        resume = resume_callback()
        try:
            self.add(resume)
            yield from _block()
        except Cancelled:
            self.discard(resume)
            raise

    async def wait(self):
        """Wait for the event to be set."""
        await self


@total_ordering
class Task:
    """The individual unit of concurrency.

    Each task has its own call stack of async functions. Tasks run until they
    complete or block. Tasks will only block at `await` statements (but not
    all `await` statements will cause the task to block).

    Additionally, each task can be cancelled.

    """
    next_id = 0
    cancellable = True

    def __init__(self, coro):
        self.id = Task.next_id
        Task.next_id += 1

        self._scheduled = False
        self.coro = coro
        self.failed = False
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
            except BaseException:
                self.failed = True
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
        for j in self.joiners:
            j(self.result)
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

        resume = resume_callback()
        try:
            self.joiners.add(resume)
            return (await _block())
        except Cancelled:
            self.joiners.discard(resume)
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
            return await _block()
        finally:
            for event_type in event_types:
                self.waiters[event_type].discard(handler)

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
        self.task_count = 0
        self.tasks = set()
        self.entered = False
        self.waiter = None

    def do(self, coro):
        task = do(coro)
        self.tasks.add(task)

        def _result(v):
            self.tasks.discard(task)
            if task.failed:
                self.cancel()
            if not self.tasks and self.waiter:
                self.waiter()

        task.joiners.add(_result)
        return task

    def cancel(self):
        for t in self.tasks:
            t.cancel()

    async def __aenter__(self):
        if self.entered:
            raise RuntimeError("Nursery cannot be entered more than once")
        self.entered = True
        return self

    async def __aexit__(self, cls, inst, tb):
        if cls:
            return self.cancel()

        if self.waiter:
            raise RuntimeError("A coroutine is already waiting on nursery exit")
        resume = resume_callback()
        self.waiter = resume
        try:
            await _block()
        except Cancelled:
            self.waiter = None
            self.cancel()
            self.tasks.clear()
            raise


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
