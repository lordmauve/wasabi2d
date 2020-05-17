Coroutines
==========

.. versionadded:: 1.3.0

``wasabi2d`` supports Python coroutines for writing asynchronous game logic
in a synchronous way.

The interface to this is ``wasabi2d.clock.coro``, or the ``coro`` attribute on
any clock instance.

.. note::

    The coroutine system does not use ``asyncio`` and is not compatible with
    ``asyncio`` loops. It only uses the ``async`` and ``await`` syntax.


Example: explosions
-------------------

Let's start with an example of what is possible. Here we use a single coroutine
to manage the whole lifecycle of a sprite.


.. code-block:: python3

    async def explode(pos):
        """Create an explosion at pos."""
        sprite = scene.layers[1].add_sprite('explosion', pos=pos)

        # Grow, rotate, and fade the sprite
        await animate(
            sprite,
            duration=0.3,
            tween='accel',
            scale=10,
            angle=10,
            color=(1, 1, 1, 0),
        )

        # Delete it again
        sprite.delete()

    clock.coro.run(explode((400, 400)))


This code isn't too dissimilar to how we might write it without the coroutine,
the only complexity being that we must pass a callable to ``on_finished``:


.. code-block:: python3

    def explode(pos):
        """Create an explosion at pos."""
        sprite = scene.layers[1].add_sprite('explosion', pos=pos)

        # Grow, rotate, and fade the sprite
        animate(
            sprite,
            duration=0.3,
            tween='accel',
            scale=10,
            angle=10,
            color=(1, 1, 1, 0),
            on_finished=sprite.delete
        )


    explode((400, 400))


But consider what happens if we want to chain several animations. This would be
very hard to express using the ``on_finished`` callbacks alone:


.. code-block:: python3

    async def explode(pos):
        """Create an explosion at pos."""
        sprite = scene.layers[1].add_sprite('explosion', pos=pos)
        sprite.color = (1, 1, 1, 0.3)

        # Explode phase
        await animate(
            sprite,
            duration=0.3,
            tween='accel',
            scale=10,
            angle=2,
            color=(1, 1, 1, 1),
        )

        # Twist phase
        await animate(
            sprite,
            duration=0.1,
            tween='accel_decel',
            angle=10,
        )

        # Collapse phase
        await animate(
            sprite,
            duration=1,
            tween='accel_decel',
            scale=1,
            pos=(pos[0] + 50, pos[1] - 50),
            color=(0, 0, 0, 0)
        )

        # Delete it again
        sprite.delete()

    clock.coro.run(explode((400, 400)))

The `full example code is here`__.

.. __: https://github.com/lordmauve/wasabi2d/blob/master/examples/coroutines/explosions.py

.. video:: _static/video/explosions.mp4


Example: enemy spawner
----------------------

Coroutines don't have to be sequential effects. A coroutine can loop for as
long as you want.

We could use an infinite loop to spawn baddies every 3 seconds:

.. code-block:: python3

    async def spawn_baddies():
        while True:
            clock.coro.run(enemy())
            await clock.coro.sleep(3)

    clock.coro.run(spawn_baddies())


Meanwhile, the behaviour of every individual baddie can be its own coroutine
instance:


.. code-block:: python3

    target = (400, 400)  # update this


    async def enemy():
        # Spawn a blob
        pos = random_pos()
        e = scene.layers[0].add_circle(
            radius=10,
            color=random_color()
            pos=pos,
        )

        # Move inexorably towards target
        async for dt in clock.coro.frames_dt():
            to_target = target - pos
            if to_target.magnitude() < e.radius:
                # We hit!
                break
            pos += to_target.normalize() * 100 * dt
            e.pos = pos

        # Explode, using the effect above
        e.delete()
        await explode(pos)


The `full example code is here`__.

.. __: https://github.com/lordmauve/wasabi2d/blob/master/examples/coroutines/run.py

.. video:: _static/video/run.mp4


Coroutine API
-------------

The ``.coro`` attribute of any :class:`Clock` is the interface to run
coroutines with that clock. This namespace distinguishes coroutine methods from
synchronous/callback methods.

First we need to be able to run and stop coroutines:

.. method:: clock.coro.run(coro)

    Launch the given coroutine instance. ``coro`` will be executed as far as
    its first ``await`` at this point.

    Return a ``Task`` instance.

    Example::

        async def myroutine(param):
            ...

        task = clock.coro.run(myroutine(param))


Tasks allow the coroutine to be cancelled (from the outside).

.. method:: task.cancel()

    Cancel the task. An exception ``clock.coro.Cancelled`` will be raised
    inside the coroutine.

    Example::

        async def myroutine():
            sprite = ...
            try:
                while True:
                    ...
            except clock.coro.Cancelled:
                sprite.delete()

        task = clock.coro.run(myroutine())
        ...
        if player.dead:
            task.cancel()


Async methods/iterators
-----------------------

Various asynchronous methods can be called inside the coroutine in order to
wait for a period of time.

.. method:: animate
    :noindex:

    You can await any animation; see :doc:`animation` for details.

    Example::

        await animate(sprite, angle=6)


.. method:: clock.coro.sleep(seconds)
    :async:

    Sleep for the given amount of time in seconds.

    Example::

        await clock.coro.sleep(10)  # sleep for 10s


.. method:: clock.coro.next_frame()
    :async:

    Sleep until the next frame. Return the interval between frames.

    Example::

        dt = await clock.coro.next_frame()


.. method:: clock.coro.frames(*, seconds=None, frames=None)
    :async:

    Iterate over multiple frames, yielding the total time waited in seconds.

    Example::

        async for t in clock.coro.frames(seconds=10):
            percent = t * 10.0
            print(f"Waiting {percent}%")

    If seconds or frames are given these are the limit on the duration of
    the loop; otherwise iterate forever.

    If limiting by seconds, you are guaranteed to receive an event after
    exactly ``seconds``, regardless of frame rate, in order to ensure that
    any effect is complete.


.. method:: clock.coro.frames_dt(*, seconds=None, frames=None)
    :async:

    Iterate over multiple frames, yielding the time difference each iteration
    in seconds.

    Example::

        async for dt in clock.coro.frames_dt(seconds=10):
            x, y = sprite.pos
            sprite.pos = (x + dt * 100, y)  # move 100 pixels per second


.. method:: clock.coro.interpolate(start, end, duration=1.0, tween='linear')
    :async:

    Interpolate between the values start and end (which must be numbers or
    tuples of numbers), over the given duration.

    This is usually less convenient than ``animate()``, but does give finer
    control.

    If ``tween`` is given it is a tweening function as described under
    :doc:`animation`.

    Example::

        async for v in clock.coro.interpolate(1, 20):
            sprite.scale = v
