The Scene
=========

.. highlight:: python

.. autoclass:: wasabi2d.Scene

    .. versionadded:: 1.4.0

        Added the `background` and `pixel_art` parameters.

The `Scene` object represents the whole graphics subsystem in wasabi2d. Scenes
manage a collection of graphical **primitives** within a number of **layers**.

Create a scene with::

    from wasabi2d import Scene

    scene = Scene(width, height)


.. attribute:: Scene.background

    Get/set the background color of the entire scene as an RGB triple. `(1, 1,
    1)` is white and `(0, 0, 0)` is black.

    You can also assign color names or HTML color codes (but the value is
    stored and returned as a tuple).


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


For split-screen or a separate HUD camera, see :ref:`viewports`.

There's also an off-screen version, which will mainly be useful for testing
and screenshotting:

.. autoclass:: wasabi2d.scene.HeadlessScene


.. _pixel-art:

Pixel Art
---------

.. versionadded:: 1.4.0

Setting ``pixel_art=True`` in the scene constructor turns off bilinear
interpolation of textures. This means that pixel edges will be clearly
visible and pixels will appear square, but may be rotated.

This is slightly different to :ref:`scene-scaling`, which applies filtering at
a higher level. In particular, scene scaling affects :doc:`effects` while
`pixel_art` mode does not. The two options can be used together or not.

Here are some examples of how sprites appear when zoomed. These differences
will be less visible without magnification.

+---------------------+----------------------------------------------+-----------------------------------------------------+
|                     | ``scaler=None``                              | ``scaler='nearest'``                                |
+---------------------+----------------------------------------------+-----------------------------------------------------+
| ``pixel_art=False`` | .. image:: _static/scaling/tank-filtered.png | .. image:: _static/scaling/tank-filtered-scaler.png |
+---------------------+----------------------------------------------+-----------------------------------------------------+
| ``pixel_art=True``  | .. image:: _static/scaling/tank-pixel.png    | .. image:: _static/scaling/tank-scaler.png          |
+---------------------+----------------------------------------------+-----------------------------------------------------+

.. _scene-scaling:

Scene scaling
-------------

.. caution:: 
    This will currently mess up things like mouse events due to the mouse pointer not matching the position of your cursor. See `this <https://github.com/pygame/pygame/issues/1365>`_.

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


.. attribute:: wasabi2d.scene.Camera.zoom

    Get/set the camera's magnification, initially ``1.0``. A value of ``2``
    draws objects twice as large. Zoom also applies to layers with zero
    parallax; use an independent viewport for an unzoomed HUD.


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


.. _viewports:

Multiple viewports
------------------

A ``Scene`` is a window with one initial viewport, available as
``scene.viewport``. A viewport defines a rectangular area of the window and
has its own camera, layers, background and rendering chain. The familiar
``scene.camera``, ``scene.layers`` and ``scene.chain`` expose the initial
viewport's objects.

Use ``Window`` directly when creating several views from scratch. For example,
this complete split-screen example shows the same world through two cameras::

    from wasabi2d import Window, run

    window = Window(800, 600)
    left = window.create_viewport(width=400, height=600, background='black')
    right = left.clone(x=400)

    left.layers[0].add_circle(radius=40, pos=(300, 300), color='orange')
    left.camera.pos = (200, 300)
    right.camera.pos = (400, 300)
    run()

``clone()`` shares the original layers and chain list, but creates a new,
independent camera. Both views show edits to the shared primitives. Camera
position and zoom are not copied; configure the new camera explicitly.
Appending to the shared chain list affects both views; assigning a new list
to one viewport's ``chain`` separates their rendering configurations.

.. method:: Window.create_viewport(width=None, height=None, x=0, y=0, background=None)

    Create and append a viewport with new, independent layers and camera.
    Omitted dimensions default to the window's logical width and height.
    Dimensions must be positive. ``background=None`` leaves the previous
    contents beneath the viewport intact; a colour clears its rectangle.

.. method:: Viewport.clone(width=None, height=None, x=None, y=None)

    Append a viewport sharing this viewport's layers and chain. Omitted
    dimensions and position are inherited, as is the background colour.

.. attribute:: Window.viewports

    The viewports in drawing order. Later entries draw over earlier ones.

.. attribute:: Viewport.layers

    The layer collection, used in the same way as ``scene.layers``.

.. attribute:: Viewport.camera

    The independent camera for this view. See :ref:`camera`.

.. attribute:: Viewport.chain

    The list of rendering operations for this view. See :ref:`chain`.

.. attribute:: Viewport.background

    The background colour, or ``None`` to skip clearing this viewport.

.. attribute:: Viewport.x
.. attribute:: Viewport.y

    The rectangle's position in logical window pixels. Unlike primitive
    coordinates, viewport rectangles use OpenGL's bottom-left origin:
    increasing ``y`` moves a viewport upwards. Primitive coordinates within
    each viewport still increase downwards.

.. attribute:: Viewport.width
.. attribute:: Viewport.height
.. attribute:: Viewport.dims

    Get/set the positive dimensions in logical pixels. ``dims`` is a pair.
    Resizing also resizes the camera's projection.

.. attribute:: Viewport.center

    Get/set the rectangle's centre in the same coordinate system as ``x``
    and ``y``.

.. attribute:: Viewport.rect

    A read-only snapshot of the rectangle as a ``pygame.Rect``. Editing this
    returned object does not change the viewport.

.. method:: Viewport.delete()

    Remove the view from the window and release its camera resources. This
    does not delete the shared primitives.

Mouse events remain in window coordinates: selecting a viewport does not
translate input into its camera's world coordinates automatically.


Layer parallax and HUDs
-----------------------

.. attribute:: Layer.parallax

    Multiplier for camera translation, defaulting to ``1.0``. Smaller values
    make a background move more slowly as the camera moves. ``0`` ignores
    camera translation, including screen shake; camera zoom still applies.

For example::

    scene.layers[-1].parallax = 0.25   # Distant background
    scene.layers[0].parallax = 1.0     # Main game world (the default)
    scene.layers[10].parallax = 0.0    # HUD unaffected by camera movement
    scene.layers[10].add_label('Score: 0', pos=(20, 30))

For a HUD that must also ignore world-camera zoom, use a separate viewport
with independent layers and camera. Create it after the world view, leave
its background as ``None``, and keep its camera at the default position and
zoom. For example, with the split-screen window above::

    hud = window.create_viewport()
    hud.layers[0].add_label('Paused', pos=(20, 30))

Put this setup before ``run()`` so the HUD is created before the game starts.
