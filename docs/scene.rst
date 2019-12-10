The Scene
=========

.. highlight:: python

.. autoclass:: wasabi2d.Scene

The `Scene` object represents the whole graphics subsystem in wasabi2d. Scenes
manage a collection of graphical **primitives** within a number of **layers**.

Create a scene with::

    from wasabi2d import Scene

    scene = Scene(width, height)



.. attribute:: Scene.background

    Get/set the background color of the entire scene as an RGB triple. `(1, 1,
    1)` is white and `(0, 0, 0)` is black.

.. attribute:: Scene.layers

    The collection of layers that will be drawn. Layers are created on access
    and do not need to be explicitly declared.

    Layers are drawn from back to front - lowest layer number to highest.

.. attribute:: Scene.title

    Get/set the caption for the window.

.. attribute:: Scene.width

    (read-only) The width of the scene in pixels.

.. attribute:: Scene.height

    (read-only) The height of the scene in pixels.


.. attribute:: Scene.camera

    (read-only) The Camera object used to render the scene. See :ref:`camera`.


There's also an off-screen version, which will mainly be useful for testing
and screenshotting:

.. autoclass:: wasabi2d.scene.HeadlessScene


.. _scene-scaling:

Scene scaling
-------------

Scene scaling allows the wasabi2d scene to be scaled independently of the
final window size. Two uses of this are:

* Supporting high dpi/retina displays with practically the same performance
  as standard displays (but reduced quality).
* Retro games, in order to draw everything pixellated.

The scene will aways have the requested dimensions, but the window will usually
be a bigger size; the biggest integer multiple that fits your screen. The
scaler in use determines how the scene is upscaled to the window.

To use this, set ``scaler`` to one of:

* ``True`` or ``'nearest'`` - nearest pixel; creates a pixellated appearance.
  Ideal for retro games.
* ``'linear'`` - linearly interpolate between pixel values.

For example, to create a retro game with a 200x100 pixel screen (very blocky
indeed), create a scene with a small viewport size, but set ``scaler`` to
``True``:

.. code-block:: python

    scene = Scene(
        width=200,
        height=120,
        scaler=True
    )

This will create a scene that is logically 200x120:

* All rendering will take place on a 200x120 frame buffer.
* Mouse coordinates will be correctly translated to scene coordinates, eg. the
  bottom right corner is ``(199, 119)``.


Coordinate system
-----------------

Unusually for an OpenGL-based game engine, wasabi2d uses Pygame's coordinate
system where the top of the screen has coordinate 0 and coordinates increase
downwards.

This allows easier porting of Pygame Zero games.

By default distances are measured in screen pixels.


.. _camera:

Camera
------

The camera for the scene is ``scene.camera``.

.. attribute:: wasabi2d.scene.Camera.pos

    Get/set the center position of the camera, as a 2D vector/pair of floats.

    Initially, this is ``(scene.width / 2, scene.height / 2)``.


.. automethod:: wasabi2d.scene.Camera.screen_shake

    Trigger a screen shake effect.

    The camera will be offset from ``.pos`` by ``dist`` in a random
    direction; then steady itself in a damped harmonic motion.

    The effect is added to the value of ``.pos``; getting/setting pos moves
    the camera independently of the shake effect.


.. _screenshot:

Screenshot and Video Recording
------------------------------

Games automatically have access to screenshot and video recording capabilities.

This is hard coded to:

* ``F12`` - take a screenshot, named with an automatic filename.
* ``Shift-F12`` - start/stop recording a video, named with an automatic
  filename.

.. versionadded:: 1.3.0

    Hard-coded screenshot/video capture to F12.

Recording video requires ``ffmpeg`` to be installed and on the ``$PATH``.

As well as this, you can use these features programmatically:

.. automethod:: wasabi2d.Scene.screenshot

.. automethod:: wasabi2d.Scene.record_video

.. automethod:: wasabi2d.Scene.stop_recording

.. automethod:: wasabi2d.Scene.toggle_recording
