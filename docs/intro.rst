Quickstart
==========

To start with, we'll create a new Python file.

The minimal boilerplate for a wasabi2d game is this::

    from wasabi2d import Scene, run

    scene = Scene()

    # The rest of your code goes here.

    run()  # keep this at the end of the file


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
    from wasabi2d import animate, event

    @event
    def on_mouse_down(pos):
        mouse_x, mouse_y = pos
        cx, cy = circle.pos

        hit = hypot(mouse_x - cx, mouse_y - cy) < circle.radius

        if hit:
            circle.radius = 50
            animate(circle, 'bounce_end', radius=30)

