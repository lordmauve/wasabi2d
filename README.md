# Wasabi 2D

A fledgling 2D graphics engine for Python, based on [moderngl], with
[pygame 2.0] for some supporting functions.

![Screenshot as of 2019-08-14](https://github.com/lordmauve/wasabi2d/raw/master/docs/2019-08-14-screenshot.png)


[moderngl]: https://github.com/moderngl/moderngl
[pygame 2.0]: https://www.pygame.org/news


Current features include:

* Sprite loading and rendering
* Rendering of text labels
* Stroked and solid-filled polygons, circles, stars, and rectangles
* Rotate, scale and move any of the above
* Sounds, keyboard and mouse events, animation/tweening, music, clocks and
  local storage
  from [Pygame Zero](https://pygame-zero.readthedocs.io/en/stable/index.html)
  (with most magic removed).


## Installation


Use pip to install the dependencies in `requirements.txt`.

```
pip install -r requirements.txt
```


## Initialising a scene


The `Scene` class holds all the renderable state. Initialising it will create a
window with the provided dimensions and set it up to be drawn.


```python
from wasabi2d import event, run, sounds, Scene, Vector2


scene = Scene(1600, 1200)
```

At the bottom of the file, call `run()` to actually run the game:

```python
run()
```


One attribute of interest is `scene.background`. This is the background color
of the entire scene as an RGB triple. `(1, 1, 1)` is white and `(0, 0, 0)` is
black.


# Coordinate system

Unusually for an OpenGL-based game engine, wasabi2d uses Pygame's coordinate
system where the top of the screen has coordinate 0 and coordinates increase
downwards.

This allows easier porting of Pygame Zero games.


# Camera

The camera is controlled by `scene.camera`. In particular, `camera.pos` is the
center position of the camera. Initially, this is `(scene.width / 2,
scene.height / 2)`.


## Creating a sprite

`scene.layers` is an automatically initialised sequence of layers. These are
drawn from lowest to highest.

To create a sprite in a layer just call `.add_sprite()`:

```python

ship = scene.layers[0].add_sprite(
    'ship',
    pos=(scene.width / 2, scene.height / 2)
)

```

Sprites must be in a directory named `images/` and must be named in lowercase
with underscores.


A sprite object has attributes that you can set:

* `.pos` - the position of the sprite

* `.angle` - a rotation in radians

* `.color` - the color to multiply the sprite with, as an RGBA tuple.
`(1, 1, 1, 1)` is opaque white.

* `.scale` - a scale factor for the sprite. 1 is original size.

* `.image` - the name of the image for the sprite.


And these methods:

* `.delete()` - delete the sprite.


# Specifying colors

Colors can be specified to any object using the attribute `color`. There are
many ways to specify color:

* tuples of 3 or 4 floats between 0 and 1 - RGB or RGBA, respectively. If 3
  numbers are given then the alpha value will be 1 (ie. opaque).
* Pygame color names like `white`, `yellow` etc,
* Hex RGB or RGBA color codes like `#eecc6688`


# Creating circles, stars, polygons

Adding shapes to the scene follows a similar API - simply pick a layer number
to add to and pass the appropriate parameters.

In general you can set these values as attributes on the returned shape.

Common attributes:

* `pos` - 2-tuple - the center point of the shape
* `fill` - `bool` - if `True`, the shape will be drawn filled. Otherwise, it
   will be drawn as an outline. This cannot currently be changed after
   creation.
* `color` - a color, as described above.
* `angle` - a rotation in radians
* `scale` - a scale factor for the shape. 1 is original size.


`Layer.add_circle(...)`

Create a circle. Takes these additional parameters.

* `radius` - `float` - the radius of the circle


`Layer.add_star(...)`

Create a star. Parameters:

* `points` - `int` - the number of points for the star.
* `outer_radius` - `float` - the radius of the tips of the points
* `inner_radius` - `float` - the radius of the inner corners of the star


`Layer.add_rect(...)`

Create a rectangle. Parameters:

* `width` - `float` - the width of the rectangle before rotation/scaling
* `height` - `float` - the height of the rectangle before rotation/scaling


`Layer.add_polygon(...)`

Create a closed polygon.

* `vertices` - sequence of `(float, float)` tuples. The vertices cannot
  currently be updated after creation.


# Text

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


# Post-processing effects

Wasabi2d provides a small number of pre-defined full-screen post processing
effects. These are defined at the layer level, and affect items in that layer
only.

The effects are described here as separate calls:


`Layer.set_effect('bloom', radius: int=...)`

Create a light bloom effect, where very bright pixels glow, making them look
exceptionally bright. The radius controls how far the effect reaches.


`Layer.set_effect('trails', fade: int=0.1)`

Apply a "motion blur" effect. Fade is the fraction of the full brightness that
is visible after 1 second.


`Layer.clear_effect()`

Remove the active effect.


## Handling events


The `@wasabi2d.event` decorator registers event handlers. The name of the
function is important; the function

```python
@event
def on_mouse_down():
```

will be called when the mouse is clicked.


The methods are exactly as described in
[Pygame Zero's documentation](https://pygame-zero.readthedocs.io/en/stable/hooks.html#event-handling-hooks),
parameters and all.

There is one exception: `update()` now takes an optional `keyboard` parameter,
as this is the normal place you would consider keyboard state.

For example:

```python

@event
def update(dt, keyboard):
    v = 20 * dt

    if keyboard.right:
        alien.pos[0] += v
    elif keyboard.left:
        alien.pos[0] -= v
    if keyboard.up:
        alien.pos[1] -= v
    elif keyboard.down:
        alien.pos[1] += v
```
