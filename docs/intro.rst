Quickstart
==========

To start with, we'll create a new Python file.

The minimal boilerplate for a wasabi2d game is this::

    import wasabi2d as w2d

    scene = w2d.Scene()

    # The rest of your code goes here.

    w2d.run()  # keep this at the end of the file


Here we create an empty scene/window, and then we start the game.

This program will pop open a black window but do nothing else. You can quit it
by clicking on the X icon or by pressing Ctrl-Q.

Let's give ourselves something to see. We'll create a green circle in the
middle of the screen. In between creating the scene
and calling ``run()``, add this code::

    circle = scene.layers[0].add_circle(
        radius=30,
        pos=(scene.width / 2, scene.height / 2),
        color='green',
    )

All objects in wasabi2d are created in **layers**. Layers are drawn from lowest
to highest and are created on demand. So the choice of ``scene.layers[0]`` is
arbitrary - but ``0`` is a good a place as any to start. Layers are added when
you access them, you don't need to create them. Scene coordinates run from
(0, 0) in the top left to (width, height) in the bottom right.

When you run the game, you'll now see a green circle in the center of the
screen. We're making progress, but this still isn't very interesting! To start
building a game we need to respond to player input. In this case, let's make
it accept mouse clicks. To do this we need to import the ``@event`` decorator
and define a function to handle a click event. We'll also use the ``animate``
function to animate an attribute over time::


    from math import hypot

    @w2d.event
    def on_mouse_down(pos):
        mouse_x, mouse_y = pos
        cx, cy = circle.pos

        hit = hypot(mouse_x - cx, mouse_y - cy) < circle.radius

        if hit:
            circle.radius = 50
            w2d.animate(circle, 'bounce_end', radius=30)


Quickstart with coroutines
--------------------------

Wasabi2D has an extensive :doc:`coroutine <coros>` based programming model and
this is the style we recommend for most programs.

Let's use coroutines to create a circle that follows the mouse.

Instead of defining event handlers, we can pass ``run()`` a coroutine object, and
await events as we choose:

.. literalinclude:: ../examples/coroutines/clicks.py

This example creates showers of particles wherever we click the mouse button.

We could instead create an emitter that tracks the mouse.

.. literalinclude:: ../examples/coroutines/drags.py
