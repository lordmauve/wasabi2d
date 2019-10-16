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

Recording video requires ``ffmpeg`` to be installed and on the ``$PATH``.

As well as this, you can use these features programmatically:

.. automethod:: wasabi2d.Scene.screenshot

.. automethod:: wasabi2d.Scene.record_video

.. automethod:: wasabi2d.Scene.stop_recording

.. automethod:: wasabi2d.Scene.toggle_recording
