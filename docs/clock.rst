.. _clock:

Clocks
======

Often when writing a game, you will want to schedule some game event to occur
at a later time. For example, we may want a big boss alien to appear after 60
seconds. Or perhaps a power-up will appear every 20 seconds.

There are also cases where you want to delay some action for a shorter
period. For example you might have a laser weapon that takes 1 second to charge
up.

We can use the ``clock`` object to schedule a function to happen in the
future.

Let's start by defining a function ``fire_laser`` that we want to run in the
future::

    def fire_laser():
        lasers.append(player.pos)

Then when the fire button is pressed, we will ask the ``clock`` to call it for
us after exactly 1 second::

    def on_mouse_down():
        clock.schedule(fire_laser, 1.0)

Note that ``fire_laser`` is the function itself; without parentheses, it is
not being called here! The clock will call it for us.

(It is a good habit to write out times in seconds with a decimal point, like
``1.0``. This makes it more obvious when you are reading it back, that you are
referring to a time value and not a count of things.)

``clock`` provides the following useful methods:

.. class:: Clock

    .. method:: schedule(callback, delay, strong=False)

        Schedule `callback` to be called after the given delay.

        Repeated calls will schedule the callback repeatedly.

        :param callback: A callable that takes no arguments.
        :param delay: The delay, in seconds, before the function should be
                      called.
        :param strong: Hold a strong reference to `callback`.

    .. method:: schedule_unique(callback, delay, strong=False)

        Schedule `callback` to be called once after the given delay.

        If `callback` was already scheduled, cancel and reschedule it. This
        applies also if it was scheduled multiple times: after calling
        ``schedule_unique``, it will be scheduled exactly once.

        :param callback: A callable that takes no arguments.
        :param delay: The delay, in seconds, before the function should be
                      called.
        :param strong: Hold a strong reference to `callback`.

    .. method:: schedule_interval(callback, interval, strong=False)

        Schedule `callback` to be called repeatedly.

        :param callback: A callable that takes no arguments.
        :param interval: The interval in seconds between calls to `callback`.
        :param strong: Hold a strong reference to `callback`.

    .. method:: each_tick(callback, strong=False)

        Schedule `callback` to be called every tick. The callback in this case
        is required to accept a parameter `dt` which is the time in seconds
        since the last tick.

        :param callback: A one argument callable.
        :param strong: Hold a strong reference to `callback`.

    .. method:: call_soon(callback)

        Schedule `callback` to be called on the next tick. Unlike most other
        clock methods, `callback` will be strongly referenced here.

        :param callback: A one argument callable.

    .. method:: unschedule(callback)

        Unschedule callback if it has been previously scheduled (either because
        it has been scheduled with ``schedule()`` and has not yet been called,
        or because it has been scheduled to repeat with
        ``schedule_interval()`` or ``each_tick()``.

    .. attribute:: coro

        Interface to asynchronous programming using coroutines, linked to this
        clock. See :doc:`coros`.

    .. method:: create_sub_clock(rate=1.0) -> SubClock

        Create a new clock that ticks when this one ticks, but potentially at
        a different rate.

Note that by default the wasabi2d clock only holds weak references to each
callback you give it. It will not fire scheduled events if the objects and
methods are not referenced elsewhere. This can help prevent the clock keeping
objects alive and continuing to fire unexpectedly after they are otherwise
dead.

Pass `strong=True` if you want the clock to hold a strong reference instead.

.. _subclocks:

Subclocks
---------

One clock is often enough for simple games, and Wasabi2D's built-in clock,
available as ``wasabi2d.clock``, is all you need. It measures time in real time
and is ticked by Wasabi2D's event loop.

But many games will need a second clock that runs at an independent rate, and
which can be paused. For example:

* All gameplay needs be paused while the menu is visible
* The menu runs with animations in real time even while gameplay is paused

You can also create slow-motion effects where the game slows down, but some
animations (maybe information like health bars and pickups) should update at
their normal rate.

A clock that runs at a fraction of a parent clock (perhaps most often the
default, real time :class:`Clock`) is a subclock and has extra methods that let
you control the rate at which it runs, or pause it independently.

Create a subclock with :meth:`Clock.create_sub_clock()` on the clock you want
it to be attached to.

.. class:: SubClock

    A clock that runs at some fraction of the rate of a parent clock.

    .. attribute:: paused

        A boolean. Set this to ``True`` to stop this clock from updating.

    .. attribute:: rate

        A float. The fraction of the speed of parent clock. 0 would be frozen,
        1.0 is full speed. A number between 0 and 1 is slow motion. A number
        greater than 1.0 would be faster motion.

    .. method:: slowmo(rate)

        A context manager to enter slow motion for the duration of a context.

        This only makes sense when used with coroutines that await during the
        context. For example::

            async def slow_mo_explosion():
                with clock.slowmo(0.5):
                    await explosion()

Subclocks can have their own subclocks.