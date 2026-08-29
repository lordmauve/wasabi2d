Coroutines
==========

.. versionadded:: 1.3.0

``wasabi2d`` supports Python coroutines for writing asynchronous game logic
in a direct, sequential style. Coroutines are particularly useful for logic
that unfolds over time: animations, enemy behaviour, levels, cut-scenes, and
input gestures.

As of Wasabi2D 2.0 the coroutine model is an implementation of structured
concurrency, similar to Trio_. It is the recommended way to structure most
Wasabi2D programs.

.. _Trio: https://trio.readthedocs.io/

.. note::

    Wasabi2D does not use ``asyncio`` or Trio and is not compatible with their
    event loops. It uses Python's ``async`` and ``await`` syntax with its own
    game loop.

.. _sc:

Your first coroutine
--------------------

A coroutine is declared with ``async def``. Pass the coroutine object returned
by calling it to :func:`wasabi2d.run`::

    import wasabi2d as w2d

    scene = w2d.Scene()

    async def main():
        circle = scene.layers[0].add_circle(
            pos=scene.dims / 2,
            radius=1,
            color='red',
        )
        await w2d.animate(circle, tween='bounce_end', radius=100)
        await w2d.clock.coro.sleep(1)
        await w2d.animate(circle, duration=0.3, radius=1)
        circle.delete()

    w2d.run(main())

The calls to ``await`` pause ``main()`` without freezing the window. Wasabi2D
continues drawing frames and processing input, then resumes the coroutine when
the animation or sleep finishes.

``w2d.run()`` keeps the game open until its main coroutine finishes. A program
with no main coroutine can still use callback-style event handlers, but a
coroutine-based program usually has one top-level ``main()`` or ``play()``
coroutine that owns the lifetime of the game.

Tie primitives to a block of code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Primitives added to a scene can be used as context managers. Exiting the
``with`` block calls the primitive's ``delete()`` method and removes it from
the scene::

    async def show_message(text):
        with scene.layers[0].add_label(
            text,
            pos=scene.dims / 2,
            align='center',
        ) as label:
            await w2d.animate(label, tween='bounce_end', scale=2)
            await w2d.clock.coro.sleep(2)

        # label has been deleted here

This is especially useful in a coroutine because the primitive remains in the
scene while the coroutine awaits. It is removed whether the block finishes
normally, raises an exception, or is cancelled.

Use ``with primitive`` whenever a primitive belongs to one piece of behaviour.
This keeps the visual object's lifetime next to the code that controls it and
prevents forgotten cleanup paths::

    async def enemy():
        with scene.layers[0].add_circle(radius=10, color='orange') as body:
            await run_enemy_ai(body)
            await w2d.animate(body, scale=0, duration=0.2)

Shapes, sprites, labels, tile maps, groups, particle groups, and particle
emitters support this pattern. Objects that do not implement the context
manager protocol should be cleaned up with ``try``/``finally`` instead::

    effect = make_external_effect()
    try:
        await use_effect(effect)
    finally:
        effect.close()

Run several behaviours together
--------------------------------

Awaiting one coroutine runs one sequence of work. Use a :class:`Nursery` when
several behaviours should overlap::

    import random

    async def animate_circle(color):
        await w2d.clock.coro.sleep(random.random())
        pos = (
            random.uniform(0, scene.width),
            random.uniform(0, scene.height),
        )

        with scene.layers[0].add_circle(
            pos=pos,
            radius=1,
            color=color,
        ) as circle:
            await w2d.animate(circle, tween='bounce_end', radius=100)
            await w2d.clock.coro.sleep(1)
            await w2d.animate(circle, duration=0.3, radius=1)

    async def main():
        async with w2d.Nursery() as nursery:
            nursery.do(animate_circle('red'))
            nursery.do(animate_circle('green'))
            nursery.do(animate_circle('blue'))

        # All three tasks have finished and all three circles are gone.

    w2d.run(main())

A nursery is an asynchronous context manager. It does not exit until every
task started with ``nursery.do()`` has finished. This gives every task a clear
owner and prevents background work from silently outliving the game state it
belongs to.

Model game structure with nested nurseries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Nurseries can be nested to match the structure of the game. For example, a
level can own all of its enemies while the game owns both the player and the
current level::

    async def do_level(level_number):
        await show_level_title(level_number)
        async with w2d.Nursery() as level:
            for _ in range(level_number):
                level.do(enemy())

    async def play():
        async with w2d.Nursery() as game:
            game.do(player())

            level_number = 1
            while True:
                await do_level(level_number)
                level_number += 1

The resulting lifetime tree is::

    play
    +-- player task
    +-- do_level
        +-- enemy task
        +-- enemy task
        +-- ...

When a scope finishes, everything below it has finished too. Code after
``do_level()`` therefore cannot accidentally overlap tasks from the previous
level.

End a group of behaviours together
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Call ``nursery.cancel()`` when one outcome should end every task in that
nursery. Cancellation propagates into child nurseries::

    async def play():
        async with w2d.Nursery() as game:
            async def player_lives():
                for _ in range(3):
                    await player()
                game.cancel()

            game.do(player_lives())

            level_number = 1
            while True:
                await do_level(level_number)
                level_number += 1

Cancellation is delivered at an ``await`` point. Context managers and
``finally`` blocks are still unwound, which is why ``with primitive`` is the
preferred cleanup style. In general, do not catch ``Cancelled`` merely to
continue running. Clean up resources and let cancellation propagate.

If a task raises an exception, its nursery cancels the nursery's other tasks,
waits for them to clean up, and propagates the error. This prevents a failing
task from leaving its siblings running in a partially broken game state.

Work with time and frames
-------------------------

Sleep and repeat
~~~~~~~~~~~~~~~~

Use :meth:`clock.coro.sleep` for a one-off delay::

    await w2d.clock.coro.sleep(0.5)

Use :meth:`clock.coro.intervals` for periodic work. It yields the total elapsed
time after each interval::

    async def spawn_enemies():
        async for elapsed in w2d.clock.coro.intervals(3):
            w2d.do(enemy())
            print(f'Enemy spawned after {elapsed:.1f} seconds')

``w2d.do()`` starts an independent task immediately. Prefer
``nursery.do()`` when the task belongs to a level, menu, entity, or other
bounded scope. Reserve ``w2d.do()`` for genuinely top-level or application
lifetime work.

Update on every frame
~~~~~~~~~~~~~~~~~~~~~

Use :meth:`clock.coro.frames_dt` when movement depends on the duration of each
frame::

    async def move_towards(sprite, target, speed):
        async for dt in w2d.clock.coro.frames_dt():
            offset = target - sprite.pos
            if offset.length() < speed * dt:
                sprite.pos = target
                return
            sprite.pos += offset.scaled_to(speed * dt)

Use :meth:`clock.coro.frames` when an effect depends on total elapsed time::

    async for elapsed in w2d.clock.coro.frames(seconds=2):
        label.text = f'{elapsed:.1f}'

A time-limited ``frames()`` iteration yields the exact final duration, even
when the last rendered frame goes past it. This makes it suitable for effects
that must finish at an exact final value.

For simple interpolation, :meth:`clock.coro.interpolate` produces values over
time::

    async for value in w2d.clock.coro.interpolate(0, 100, duration=1):
        meter.width = value

Most primitive attributes are more conveniently changed with
:func:`wasabi2d.animate`, which is itself awaitable::

    await w2d.animate(sprite, pos=target, duration=1)

Use the clock that owns the behaviour
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Coroutine timing methods belong to a clock. The default
``w2d.clock.coro`` follows real game time. A subclock's coroutine methods
follow that subclock, including its pause state and rate. This lets gameplay
pause while menu animation continues::

    game_clock = w2d.clock.create_sub_clock()

    async def gameplay():
        async for dt in game_clock.coro.frames_dt():
            update_world(dt)

See :ref:`subclocks` for creating, pausing, and changing the rate of subclocks.

Handle input from coroutines
----------------------------

Wait for one event
~~~~~~~~~~~~~~~~~~

Use :func:`wasabi2d.next_event` when the next matching event is all that
matters. Event types can be Pygame constants or Wasabi2D's string names::

    import pygame

    event = await w2d.next_event(pygame.MOUSEBUTTONDOWN, button=1)
    print(event.pos)

This subscribes only while ``next_event()`` is being awaited. An event that
occurs while the coroutine is doing something else is not retained. That is
usually desirable for isolated interactions such as "press a key to
continue".

Subscribe to a sequence of events
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :meth:`events.subscribe` when every event in a sequence matters, such as a
drag gesture. The subscription remains active for the lifetime of the
asynchronous iterator and queues matching events::

    async def drag_circle(circle):
        await w2d.next_event(pygame.MOUSEBUTTONDOWN, button=1)

        async for event in w2d.events.subscribe(
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONUP,
        ):
            if event.type == pygame.MOUSEBUTTONUP:
                return
            circle.pos = event.pos

The queue means events are not missed while the loop body awaits, but it can
grow without bound if events arrive faster than they are processed. Keep the
loop body quick, or use a higher-level input helper that coalesces events.

Handle multiple touches
~~~~~~~~~~~~~~~~~~~~~~~

``events.next_touch()`` returns an asynchronous iterator for one finger, from
the initial down event through its motion events to the final up event. Start
one task per touch to support multi-touch::

    async def follow_touch(first_event, touch):
        with particles.add_emitter(
            pos=(
                first_event.x * scene.width,
                first_event.y * scene.height,
            ),
            rate=100,
        ) as emitter:
            async for event in touch:
                emitter.pos = (
                    event.x * scene.width,
                    event.y * scene.height,
                )

    async def touches():
        async with w2d.Nursery() as nursery:
            while True:
                touch = w2d.events.next_touch()
                first_event = await touch.__anext__()
                nursery.do(follow_touch(first_event, touch))

The first event is consumed to ensure that the touch has started before its
task is added to the nursery. The remaining iterator still contains subsequent
motion and up events.

Common patterns
---------------

Wait for several operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :func:`wasabi2d.gather` when you only need to start several coroutines and
wait until all of them finish::

    await w2d.gather(
        w2d.animate(title, pos=(400, 200)),
        play_intro_music(),
        preload_level(),
    )

Use a nursery instead when you need to add tasks over time, keep their returned
task objects, or cancel the group explicitly.

Wait for a task's result
~~~~~~~~~~~~~~~~~~~~~~~~

``nursery.do()`` and ``w2d.do()`` return a :class:`Task`. Await
``task.join()`` to retrieve the coroutine's return value::

    async with w2d.Nursery() as nursery:
        task = nursery.do(load_level_data())
        await show_loading_animation()
        level_data = await task.join()

Usually it is simpler to directly ``await load_level_data()``. A task is useful
when that operation must overlap other work.

Time out optional work
~~~~~~~~~~~~~~~~~~~~~~

Use :meth:`clock.coro.move_on_after` to cancel the current block after a clock
duration and then continue after the block::

    with w2d.clock.coro.move_on_after(5):
        event = await w2d.next_event(pygame.KEYDOWN)
        choose_key(event.key)

    # Reached after a key press or after five seconds.

The timeout follows the clock on which ``move_on_after()`` was called. A
timeout on a paused subclock remains paused too. Resources created inside the
block should use context managers or ``finally`` so they are cleaned up when
the timeout cancels the block.

Signal between tasks
~~~~~~~~~~~~~~~~~~~~

Use :class:`Event` for a condition that one task sets and one or more tasks
await::

    level_ready = w2d.Event()

    async def loader():
        await load_level()
        level_ready.set()

    async def player():
        await level_ready
        start_playing()

An event remains set until ``reset()`` is called. Awaiting an already-set event
returns immediately. It carries no value; use ordinary shared state for data
that accompanies the signal.

Choosing the right construct
----------------------------

The coroutine tools solve different lifetime and waiting problems:

* Direct ``await`` means "do this next and use its result."
* ``async with Nursery()`` means "these tasks belong to this block."
* ``nursery.do()`` means "start this sibling task in the current scope."
* ``w2d.do()`` means "start application-lifetime work with no local owner."
* ``with primitive`` means "this scene object belongs to this block."
* ``async for`` over clock methods means "update on repeated clock ticks."
* ``next_event()`` means "wait for the next matching input event."
* ``events.subscribe()`` means "retain every matching event in this sequence."
* ``Event`` means "wait until another task announces a condition."
* ``move_on_after()`` means "give this work a time budget, then continue."

The common idea is ownership. A game state should own its tasks, and each task
should own the scene objects and other resources it controls. When the game
state ends, Python's normal block unwinding then cleans up the entire subtree.

Coroutine reference
-------------------

Starting and grouping tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. function:: wasabi2d.run(main=None)

    Run the Wasabi2D event loop. If ``main`` is a coroutine object, start it
    as the main task and keep running until it finishes.

.. function:: wasabi2d.do(coro)

    Start a coroutine or awaitable as an independent task. It begins running
    immediately and returns a :class:`Task`.

    Prefer :meth:`Nursery.do` for work with a bounded lifetime.

.. class:: Nursery

    An asynchronous context manager that owns a group of tasks. On normal
    exit, it waits for all tasks. On cancellation or error, it cancels them,
    waits for cleanup, and then exits or propagates the error.

    .. method:: do(coro)

        Start ``coro`` in the nursery and return its :class:`Task`.

    .. method:: cancel()

        Cancel the code running inside the nursery and every task owned by it.

.. class:: Task

    A running coroutine returned by ``w2d.do()`` or ``nursery.do()``.

    .. method:: cancel()

        Request cancellation. Cancellation is raised inside the coroutine at
        an await point.

    .. method:: join()
        :async:

        Wait for the task to finish and return the coroutine's return value.

    .. attribute:: finished

        Whether the task has finished.

    .. attribute:: failed

        Whether the task finished by raising an exception.

    .. attribute:: result

        The task's return value after it has finished successfully.

.. function:: wasabi2d.gather(*coros)

    Start all the given coroutines in a nursery and wait for all of them to
    finish.

Synchronization
~~~~~~~~~~~~~~~

.. class:: Event

    A persistent boolean signal that tasks can await.

    .. method:: set()

        Set the event and wake every waiting task. Future waits return
        immediately until the event is reset.

    .. method:: reset()

        Clear the event so future waits block.

    .. method:: wait()
        :async:

        Wait until the event is set. ``await event`` is equivalent.

    .. method:: is_set()

        Return whether the event is currently set. ``bool(event)`` is
        equivalent.

Input
~~~~~

.. function:: wasabi2d.next_event(*event_types, **attrs)

    Wait for and return the next Pygame event matching one of ``event_types``
    and all the given event attributes.

.. method:: events.subscribe(*event_types, **attrs)
    :async:

    Return an asynchronous iterator that queues and yields all matching events
    until the iterator is closed or cancelled.

.. method:: events.next_touch()
    :async:

    Return an asynchronous iterator over the events for the next touch,
    including finger down, motion, and finger up.

Clock operations
~~~~~~~~~~~~~~~~

Each clock has a ``coro`` namespace. Operations use that clock's time, rate,
and pause state.

.. method:: clock.coro.sleep(seconds)
    :async:

    Wait for ``seconds`` on the clock and return the actual elapsed clock time.

.. method:: clock.coro.intervals(seconds)
    :async:

    Iterate forever at the given interval, yielding total elapsed clock time.

.. method:: clock.coro.next_frame()
    :async:

    Wait for the next tick of this clock and return the elapsed time since its
    previous tick.

.. method:: clock.coro.frames(*, seconds=None, frames=None)
    :async:

    Iterate over clock frames, yielding total elapsed time. Pass either
    ``seconds`` or ``frames`` to limit the iteration; pass neither to iterate
    forever.

.. method:: clock.coro.frames_dt(*, seconds=None, frames=None)
    :async:

    Iterate over clock frames, yielding the elapsed time for each frame. The
    optional limits are the same as for :meth:`clock.coro.frames`.

.. method:: clock.coro.interpolate(start, end, duration=1.0, tween='linear')
    :async:

    Iterate over interpolated values from ``start`` to ``end``. Values may be
    numbers or tuples of numbers. ``tween`` uses the names documented under
    :doc:`animation`.

.. method:: clock.coro.move_on_after(seconds)

    Return a synchronous context manager that cancels its block after
    ``seconds`` of clock time, absorbs that cancellation, and continues after
    the block.

.. method:: clock.coro.run(coro)

    Deprecated alias for :func:`wasabi2d.do`. New code should use
    ``w2d.do(coro)`` or ``nursery.do(coro)``.

Awaitable animation
~~~~~~~~~~~~~~~~~~~

.. function:: wasabi2d.animate(object, tween='linear', duration=1, **targets)
    :noindex:

    Animate attributes of ``object`` and return an awaitable animation. See
    :doc:`animation` for all options.
