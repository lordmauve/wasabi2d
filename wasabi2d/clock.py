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
from contextlib import contextmanager

from moderngl import context

from . import loop


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


class Coroutines:
    """Namespace for coroutine operations on a clock."""

    # Alias for backwards compatibility
    Cancelled = loop.Cancelled

    def __init__(self, clock):
        self.clock = clock

    async def sleep(self, seconds: float) -> float:
        """Sleep for the given time in seconds.

        Return the exact time slept for.
        """
        t = self.clock.t
        resume = loop.resume_callback()
        self.clock.schedule(resume, seconds, strong=True)

        try:
            await loop._block()
        except loop.Cancelled:
            self.clock.unschedule(resume)
            raise
        return self.clock.t - t

    async def next_frame(self):
        """Await the next frame. Return the time elapsed."""
        while True:
            start = self.clock.t

            # FIXME: should use *clock* ticks not event loop ticks
            await loop.next_tick()

            dt = self.clock.t - start
            if dt:
                return dt

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

    @contextmanager
    def move_on_after(self, seconds):
        from .loop import CancelScope
        scope = CancelScope()
        self.clock.schedule(scope.cancel, seconds, strong=True)
        with scope:
            yield
            self.clock.unschedule(scope.cancel)

    def run(self, coro):
        """Schedule a coroutine."""
        import warnings
        warnings.warn(
            "clock.coro.run is deprecated",
            DeprecationWarning,
            stacklevel=2
        )
        return loop.do(coro)


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

    def animate(
            self,
            object,
            tween='linear',
            duration=1,
            on_finished=None,
            **targets,
        ):
        """Interpolate some attributes of object using this clock."""
        from .animation import Animation
        return Animation(
            object,
            tween,
            duration,
            on_finished=on_finished,
            clock=self,
            **targets
        )

    def create_sub_clock(self, rate=1.0) -> 'SubClock':
        """Create a new clock attached to this one.

        The new clock ticks when this one ticks, but can tick at a different
        rate and be paused independently.

        """
        return SubClock(self, rate)


class SubClock(Clock):
    """A clock which has a parent clock controlling when it ticks."""
    rate: float

    def __init__(self, parent: Clock, rate=1.0):
        self._paused = True
        self.parent = parent
        self.rate = 1.0
        super().__init__()

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, v):
        v = bool(v)
        if v == self._paused:
            return
        if v:
            self.parent.unschedule(self._tick_from)
        else:
            self.parent.each_tick(self._tick_from, strong=True)
        self._paused = v

    def _tick_from(self, dt):
        if self.rate:
            self.tick(dt * self.rate)

    def delete(self):
        """Delete this subclock."""
        self.paused = True

    @contextmanager
    def slowmo(self, rate):
        """Slow down this clock within the context.

        This is only useful within a coroutine.
        """
        prev_rate = self.rate
        self.rate = rate
        try:
            yield
        finally:
            self.rate = prev_rate


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
create_sub_clock = clock.create_sub_clock
