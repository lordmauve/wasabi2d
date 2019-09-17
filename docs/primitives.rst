Primitives
==========

Graphical objects that can be drawn by the :class:`Scene` are called
**primitives**.

Wasabi2d offers many different types of primitives:

* Polygons, both filled and stroked
* Sprites
* Text
* Particle groups

.. _colors:

Specifying colors
-----------------

Colors can be specified to any object using the attribute `color`. There are
many ways to specify color:

* tuples of 3 or 4 floats between 0 and 1 - RGB or RGBA, respectively. If 3
  numbers are given then the alpha value will be 1 (ie. opaque).
* Pygame color names like `white`, `yellow` etc,
* Hex RGB or RGBA color codes like `#eecc6688`


Common Attributes
-----------------

Most primitives support attributes for transforming the position, rotation,
scale and color of the object.

You can pass these as keyword arguments to the factory function, or you can
set them on the primitive object.

Common attributes:

.. attribute:: pos

    2-tuple of floats - the "center" point of the shape

.. attribute:: scale

    A scale factor for the shape. 1 is original size.

.. attribute:: color

    The color of the shape, as :ref:`described above <colors>`.

.. attribute:: angle

    The rotation of the object, as an angle in radians. Because of the
    coordinate system in wasabi2d, increasing angle gives a clockwise
    rotation.



Creating a sprite
-----------------

`scene.layers` is an automatically initialised sequence of layers. These are
drawn from lowest to highest.

To create a sprite in a layer just call `.add_sprite()`::

    ship = scene.layers[0].add_sprite(
        'ship',
        pos=(scene.width / 2, scene.height / 2)
    )

Sprites must be in a directory named ``images/`` and must be named in lowercase
with underscores. This restriction ensures that games written with wasabi2d
will work on with case sensitive and insensitive filenames.


A sprite object has attributes that you can set:

* ``.pos`` - the position of the sprite

* ``.angle`` - a rotation in radians

* ``.color`` - the color to multiply the sprite with, as an RGBA tuple.
  ``(1, 1, 1, 1)`` is opaque white.

* ``.scale`` - a scale factor for the sprite. 1 is original size.

* ``.image`` - the name of the image for the sprite.


And these methods:

* ``.delete()`` - delete the sprite.


Circles
-------

`Layer.add_circle(...)`

Create a circle. Takes these additional parameters.

* `radius` - `float` - the radius of the circle
* `fill` - `bool` - if `True`, the shape will be drawn filled. Otherwise, it
   will be drawn as an outline. This cannot currently be changed after
   creation.


Stars
-----

`Layer.add_star(...)`

Create a star. Parameters:

* `points` - `int` - the number of points for the star.
* `outer_radius` - `float` - the radius of the tips of the points
* `inner_radius` - `float` - the radius of the inner corners of the star
* `fill` - `bool` - if `True`, the shape will be drawn filled. Otherwise, it
   will be drawn as an outline. This cannot currently be changed after
   creation.


Rectangles
----------

`Layer.add_rect(...)`

Create a rectangle. Parameters:

* `width` - `float` - the width of the rectangle before rotation/scaling
* `height` - `float` - the height of the rectangle before rotation/scaling
* `fill` - `bool` - if `True`, the shape will be drawn filled. Otherwise, it
   will be drawn as an outline. This cannot currently be changed after
   creation.


Polygons
--------

`Layer.add_polygon(...)`

Create a closed polygon.

* `vertices` - sequence of `(float, float)` tuples. The vertices cannot
  currently be updated after creation.
* `fill` - `bool` - if `True`, the shape will be drawn filled. Otherwise, it
   will be drawn as an outline. This cannot currently be changed after
   creation.


Text
----

wasabi2d supports text labels. The fonts for the labels must be in the `fonts/`
directory in TTF format, and have names that are `lowercase_with_underscores`.


`Layer.add_label(...)`

Create a text label.

* `text` - `str` - the text of the label
* `font` - `str` - the name of the font to load
* `fontsize` - `float` - the size of the font, in pixels. The actual height of
  the characters may differ due to the metrics of the font.
* `align` - `str` - one of `'left'`, `'center'`, or `'right'`. This controls
  how the text aligns relative to `pos`.

