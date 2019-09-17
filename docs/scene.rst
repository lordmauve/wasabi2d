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

    The background color of the entire scene as an RGB triple. `(1, 1, 1)` is
    white and `(0, 0, 0)` is black.

.. attribute:: Scene.layers

    The collection of layers that will be drawn. Layers are created on access
    and do not need to be explicitly declared.

    Layers are drawn from back to front - lowest layer number to highest.


Coordinate system
-----------------

Unusually for an OpenGL-based game engine, wasabi2d uses Pygame's coordinate
system where the top of the screen has coordinate 0 and coordinates increase
downwards.

This allows easier porting of Pygame Zero games.


Specifying colors
-----------------

Colors can be specified to any object using the attribute `color`. There are
many ways to specify color:

* tuples of 3 or 4 floats between 0 and 1 - RGB or RGBA, respectively. If 3
  numbers are given then the alpha value will be 1 (ie. opaque).
* Pygame color names like `white`, `yellow` etc,
* Hex RGB or RGBA color codes like `#eecc6688`


Camera
------

The camera is controlled by `scene.camera`. In particular, `camera.pos` is the
center position of the camera. Initially, this is `(scene.width / 2,
scene.height / 2)`.
