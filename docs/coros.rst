Coroutines
==========

.. versionadded:: 1.3.0

``wasabi2d`` supports Python coroutines for writing asynchronous game logic
in a synchronous way.

As of Wasabi2D 2.0 the coroutine model is a full implementation of structured
concurrency, similar to Trio_. This powerful approach is the recommended way
of working with Wasabi2D.

.. _Trio: https://trio.readthedocs.io/

.. note::

    The coroutine system does not use ``asyncio``, or Trio, and is not
    compatible with their event loops. It only uses the ``async`` and
    ``await`` syntax.

.. _sc:

Structured Concurrency Quickstart
---------------------------------

To run a Wasabi2D game with structured concurrency, pass a coroutine object
to ``wasabi2d.run()``::

    import wasabi2d as w2d

    scene = w2d.Scene()

    async def main():
        with scene.add_circle(
            pos=scene.dims / 2,
            radius=scene.dims.length() / 2,
            color='red'
        ) as c:
            await w2d.animate(c, tween='bounce_end', radius=100)
            await w2d.clock.coro.sleep(3)
            await w2d.animate(c, duration=0.3, radius=1)
        await w2d.clock.coro.sleep(3)

    w2d.run(main())

This animates a circle shape, which "drops" into place, waits a few seconds,
then shrinks away.

Here we're using the circle shape as a context manager, which deletes it when
the context exits. (This feature is only useful with coroutines; if you don't
``await`` within the context then the object would be deleted before it is
ever drawn to the screen.)

``w2d.run()`` does not return until the coroutine it was passed has completed.
This means that it is only suitable for doing one thing at a time. To run
multiple tasks in parallel, we use a nursery - a scope within which those
tasks will run. By the time the nursery has finished all the tasks will have
finished::

    import wasabi2d as w2d
    import random

    scene = w2d.Scene()

    async def animate_circle(color):
        await w2d.clock.coro.sleep(random.random())

        w, h = scene.dims
        pos = random.uniform(0, w), random.uniform(0, h)

        with scene.add_circle(
            pos=pos,
            radius=scene.dims.length() / 2,
            color=color
        ) as c:
            await w2d.animate(
                c,
                tween='bounce_end',
                radius=100
            )
            await w2d.clock.coro.sleep(3)
            await w2d.animate(c, duration=0.3, radius=1)

    async def main():
        async with w2d.Nursery() as ns:
            ns.do(animate_circle('red'))
            ns.do(animate_circle('green'))
            ns.do(animate_circle('blue'))
            ns.do(animate_circle('yellow'))
            ns.do(animate_circle('magenta'))

        # All circles have disappeared
        await w2d.clock.coro.sleep(3)

    w2d.run(main())

Here we've created 5 tasks, each animating their own circle. Due to random
delays they will take different amounts of time to animate. Still, we know that
by the time the context has exited all of the circles will have finished.

Here we're using fixed animations. But the tasks don't need to be so rigid. A
task could represent an enemy, and stay alive until the enemy is killed. So the
nursery will not exit until all enemies have been killed. That means you can
write one coroutine that manages a whole level::

    async def do_level(level_number):
        await show_level_title(f"Level {level_number}")
        async with w2d.Nursery() as ns:
            for _ in range(level_number):
                ns.do(enemy())

And we can wrap that up to play a sequence of levels. Let's imagine we have a
coroutine that controls the player. The player will survive multiple levels so
we can run that with an *outer* nursery::

    async def play():
        async with w2d.Nursery() as game:
            game.do(player())
            level = 1
            while True:
                await do_level(level)
                await w2d.clock.coro.sleep(3)

This is enough to do lots of interesting things, but what happens if the player
dies? The ``player()`` task completes, but the level stays alive. To handle
this situation we allow nurseries to be cancelled::

    async def play():
        async with w2d.Nursery() as game:
            async def player_lives():
                for _ in range(3):  # give the player 3 lives
                    await player()
                game.cancel()  # end the game

            game.do(player_lives())
            level = 1
            while True:
                await do_level(level)
                await w2d.clock.coro.sleep(3)

When a nursery is cancelled, all tasks within it are terminated with an
exception. This propagates into tasks that contain their own nurseries. Here
the context manager we used becomes important again. Remember we wrote code
like::

    async def player():
        with scene.add_sprite() as ship:
            ...

Using context managers ensures the objects we added to a scene are removed when
their task is cancelled. So both drawn primitives and the behaviours that
control them are scoped to a block of code.


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
