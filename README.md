# Wasabi 2D

A fledgling 2D graphics engine for Python, based on [moderngl], with
[pygame 2.0] for some supporting functions.


[moderngl]: https://github.com/moderngl/moderngl
[pygame 2.0]: https://www.pygame.org/news


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


## Creating a sprite

`scene.layers` is an automatically initialised sequence of layers. These are
drawn from lowest to highest.

To create a sprite in a layer just call `.add_sprite()`:

```python

ship = scene.layers[0].add_sprite(
    'ship.png',
    pos=(scene.width / 2, scene.height / 2)
)

```

A sprite object has attributes that you can set:

`.pos` - the position of the sprite

`.angle` - a rotation in radians

`.color` - the color to multiply the sprite with, as an RGBA tuple.
`(1, 1, 1, 1)` is opaque white.

`.scale` - a scale factor for the sprite. 1 is original size.

And these methods:

`.delete()` - delete the sprite.


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
