"""Clock/event scheduler.

This is a Pygame implementation of a scheduler inspired by the clock
classes in Pyglet.

This clock holds weak references to callbacks by default. This is useful to
avoid accidentally "leaking" objects; with strong references it is very easy
to accidentally create a situation where a leaked object is perpetually being
updated even though nothing else references it. Weak references ensure that
objects are only updated if they are referenced elsewhere.

"""
import heapq
import warnings
from weakref import ref
from itertools import chain, count
from functools import total_ordering
from collections import namedtuple
from types import MethodType
import types


__all__ = [
    'Clock', 'schedule', 'schedule_interval', 'unschedule',
    'schedule_unique', 'each_tick', 'call_soon', 'coro',
]

# This type can't be weakreffed in Python 3.4
builtin_function_or_method = type(open)


def weak_method(method):
    """Quick weak method ref in case users aren't using Python 3.4"""
    selfref = ref(method.__self__)
    funcref = ref(method.__func__)

    def weakref():
        self = selfref()
        func = funcref()
        if self is None or func is None:
            return None
        return func.__get__(self)
    return weakref


def mkref(o):
    if isinstance(o, MethodType):
        return weak_method(o)
    else:
        try:
            return ref(o)
        except TypeError:
            if isinstance(o, builtin_function_or_method):
                return lambda: o
            raise


@total_ordering
class Event:
    """An event scheduled for a future time.

    Events are ordered by their scheduled execution time.

    """
    def __init__(self, time, cb, strong=False, repeat=None):
        self.time = time
        self.repeat = repeat
        self.cb = mkref(cb) if not strong else lambda: cb
        self.name = str(cb)
        self.repeat = repeat

    def __lt__(self, ano):
        return self.time < ano.time

    def __eq__(self, ano):
        return self.time == ano.time

    @property
    def callback(self):
        return self.cb()


WaitDelay = namedtuple('Delay', 'seconds')
WaitTick = object()


class Future:
    """An object that can be awaited.

    When awaited, yield a value that indicates the event to wait for.
    """
    __slots__ = ('val', 'awaited')

    def __init__(self, val):
        self.val = val
        self.awaited = False

    def __await__(self):
        self.awaited = True
        yield self

    def __del__(self):
        if not self.awaited:
            warnings.warn(ResourceWarning("wasabi2d future was not awaited"))


class WaitEvent:
    """Await some condition that will arise in future."""
    def __init__(self):
        self.done = False
        self._result = None
        self._on_ready = None

    def when_ready(self, callback):
        self._on_ready = callback
        if self.done:
            callback()

    def set(self, result):
        """Set the result for the event."""
        self.done = True
        self._result = result
        self._on_ready()

    def get_result(self):
        """Get the result."""
        if not self.done:
            raise ValueError("Event is not complete.")
        return self._result


class Coroutines:
    """Namespace for coroutine operations on a clock."""

    class Cancelled(Exception):
        """Raised inside a coroutine when a task is cancelled."""

    def __init__(self, clock):
        self.clock = clock
        self._ready_events = set()

    def _delay(self, seconds):
        """Get a future for a delay."""
        return Future(WaitDelay(seconds))

    def _frame(self):
        """Get a future for the next frame."""
        return Future(WaitTick)

    def _event(self):
        return Future(WaitEvent())

    async def sleep(self, seconds):
        """Sleep for the given time in seconds."""
        await self._delay(seconds)
        return seconds

    async def next_frame(self):
        """Await the next frame. Return the time elapsed."""
        start = self.clock.t
        await self._frame()
        return self.clock.t - start

    async def frames(self, *, seconds=None, frames=None):
        """Iterate over multiple frames, yielding the total time.

        For example::

            async for t in clock.coro.frames(seconds=10):
                percent = t * 10.0
                print(f"Waiting {percent}%")

        If seconds or frames are given these are the limit on the duration of
        the loop; otherwise iterate forever.

        If limiting by seconds, you are guaranteed to receive an event after
        exactly ``seconds``, regardless of frame rate, in order to ensure that
        any effect is complete.

        """
        if seconds is not None and frames is not None:
            raise TypeError("Only seconds or frames may be given, not both.")

        start = self.clock.t
        for f in count(1):
            await self.next_frame()
            now = self.clock.t - start
            if seconds is not None and now >= seconds:
                yield seconds
                return

            yield now
            if f == frames:
                break

    async def frames_dt(self, *, seconds=None, frames=None):
        """Iterate over multiple frames, yielding the time per frame."""
        last_t = 0
        async for t in self.frames(seconds=seconds, frames=frames):
            yield t - last_t
            last_t = t

    async def interpolate(self, start, end, duration=1.0, tween='linear'):
        """Iterate over values between start and end, over the given duration.

        The values of 'tween' are as for animate().

        For example,

            async for pos in clock.coro.tween(ship.pos, target_pos, 1.0):
                space_ship.pos = pos

        """
        from . import animation
        func = animation.TWEEN_FUNCTIONS[tween]

        async for t in self.frames(seconds=duration):
            if t >= duration:
                yield end
                return
            frac = func(t / duration)
            yield animation.tween_attr(frac, start, end)

    def run(self, coro):
        """Schedule a coroutine."""
        assert isinstance(coro, types.CoroutineType)
        task = Task(self.clock, coro)
        return task


class Task:
    def __init__(self, clock, coro):
        self.clock = clock
        self.coro = coro
        self.result = None
        self._step()

    def _step(self, await_value=None):
        """Step this task, passing the given value that was awaited.

        For time events, await_value will be a time delta in seconds; for
        condition events, it will be some other value.

        """
        clock = self.clock
        clock.unschedule(self._step)

        if self.coro is None:
            return

        try:
            res = self.coro.send(await_value)
        except StopIteration as stop:
            if stop.args:
                self.result = stop.args[0]
            return

        if not isinstance(res, Future):
            raise TypeError(
                f"Unable to await {res!r} with "
                "clock.coro.run(). wasabi2d coroutines are not "
                "compatible with asyncio."
            )

        val = res.val
        if isinstance(val, WaitDelay):
            clock.schedule(self._step, val.seconds, strong=True)
        elif val is WaitTick:
            clock.call_soon(self._step)
        elif isinstance(val, WaitEvent):
            # Bit ugly
            val.when_ready(
                lambda: clock.call_soon(
                    lambda dt: self._step(val._result)
                )
            )
        else:
            raise TypeError("Unexpected value")

    def cancel(self):
        """Cancel the task."""
        try:
            self.coro.throw(Coroutines.Cancelled)
        except (StopIteration, Coroutines.Cancelled):
            # Coroutine halted successfully. If not it may be awaiting
            # something during exception handling, and we should not unschedule
            # it.
            self.clock.unschedule(self._step)
            self.coro = None


class Clock:
    """A clock used for event scheduling.

    When tick() is called, all events scheduled for before now will be called
    in order.

    tick() would typically be called from the game loop for the default clock.

    Additional clocks could be created - for example, a game clock that could
    be suspended in pause screens. Your code must take care of calling tick()
    or not. You could also run the clock at a different rate if desired, by
    scaling dt before passing it to tick().

    """
    def __init__(self):
        self.t = 0
        self.paused = False
        self.fired = False
        self.events = []
        self._each_tick = []
        self._next_tick = []
        self.coro = Coroutines(self)

    def clear(self):
        """Remove all handlers from this clock."""
        self.events.clear()
        self._each_tick.clear()

    def schedule(self, callback, delay, *, strong=False):
        """Schedule callback to be called once, at `delay` seconds from now.

        :param callback: A parameterless callable to be called.
        :param delay: The delay before the call (in clock time / seconds).

        """
        heapq.heappush(
            self.events,
            Event(self.t + delay, callback, strong, None)
        )

    def schedule_unique(self, callback, delay, *, strong=False):
        """Schedule callback to be called once, at `delay` seconds from now.

        If it was already scheduled, postpone its firing.

        :param callback: A parameterless callable to be called.
        :param delay: The delay before the call (in clock time / seconds).

        """
        self.unschedule(callback)
        self.schedule(callback, delay, strong=strong)

    def schedule_interval(self, callback, delay, *, strong=False):
        """Schedule callback to be called every `delay` seconds.

        The first occurrence will be after `delay` seconds.

        :param callback: A parameterless callable to be called.
        :param delay: The interval in seconds.

        """
        heapq.heappush(
            self.events,
            Event(self.t + delay, callback, strong, delay)
        )

    def unschedule(self, callback):
        """Unschedule the given callback.

        If scheduled multiple times all instances will be unscheduled.

        """
        self.events = [
            e for e in self.events
            if e.callback != callback and e.callback is not None
        ]
        heapq.heapify(self.events)
        self._each_tick = [e for e in self._each_tick if e() != callback]

    def call_soon(self, callback):
        """Schedule a function to be called on the next tick.

        The function will receive a parameter `dt` indicating the time that
        has passed.

        The callback will always be strongly referenced.

        """
        self._next_tick.append(lambda: callback)

    def each_tick(self, callback, strong=False):
        """Schedule a callback to be called every tick.

        Unlike the standard scheduler functions, the callable is passed the
        elapsed clock time since the last call (the same value passed to tick).

        """
        self._each_tick.append(
            (lambda: callback) if strong else mkref(callback)
        )

    def _fire_each_tick(self, dt):
        dead = [
            None,  # None means a weak ref has expired, always remove
        ]
        to_fire = chain(self._next_tick, self._each_tick)
        self._next_tick = []
        for r in to_fire:
            cb = r()
            if cb is not None:
                self.fired = True
                try:
                    cb(dt)
                except Exception:
                    import traceback
                    traceback.print_exc()
                    dead.append(cb)
        self._each_tick = [e for e in self._each_tick if e() not in dead]

    def tick(self, dt: float) -> bool:
        """Update the clock time and fire all scheduled events.

        :param dt: The elapsed time in seconds.
        :return bool: Return True if any callback was triggered.

        """
        if self.paused:
            return False
        self.fired = False
        self.dt = dt = float(dt)
        self.t += dt
        self._fire_each_tick(dt)
        while self.events and self.events[0].time <= self.t:
            ev = heapq.heappop(self.events)
            cb = ev.callback
            if not cb:
                continue

            if ev.repeat is not None:
                self.schedule_interval(cb, ev.repeat)

            self.fired = True
            try:
                cb()
            except Exception:
                import traceback
                traceback.print_exc()
                self.unschedule(cb)
        return self.fired


# One instance of a clock is available by default, to simplify the API
default_clock = clock = Clock()
tick = clock.tick
schedule = clock.schedule
schedule_interval = clock.schedule_interval
schedule_unique = clock.schedule_unique
unschedule = clock.unschedule
each_tick = clock.each_tick
call_soon = clock.call_soon
coro = clock.coro
