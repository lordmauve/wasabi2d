# ![Wasabi 2D](https://raw.githubusercontent.com/lordmauve/wasabi2d/master/docs/_static/wasabi2d.png)

![PyPI](https://img.shields.io/pypi/v/wasabi2d) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wasabi2d) ![PyPI - Wheel](https://img.shields.io/pypi/wheel/wasabi2d)

[![Discord](https://img.shields.io/discord/705530610847973407)](https://discord.gg/jBWaWHU)

A fast, cutting-edge 2D game engine for Python.

Current features include:

* Sprites, text, and stroked and filled polygons - all rotatable, scalable, and
  colorizeable
* A [coroutine programming model]() for easy animated effects.
* [Particle systems](https://wasabi2d.readthedocs.io/en/latest/coros.html)
* [Built-in post-processing effects](https://wasabi2d.readthedocs.io/en/latest/effects.html) using GLSL shaders.
* Sound, music and tone generation.
* Event driven input handling for keyboard and mouse.
* Animation/tweening.
* "Local storage" to easily save state.

Wasabi2D is based on [moderngl], with [pygame 2.0] for some supporting functions, and supporting APIs ported from [Pygame Zero](https://github.com/lordmauve/pgzero).



[moderngl]: https://github.com/moderngl/moderngl
[pygame 2.0]: https://www.pygame.org/news

## Quick example

Draw a drop-shadowed circle that follows the mouse:

```python
import wasabi2d as w2d

scene = w2d.Scene()
scene.background = 0.9, 0.9, 1.0

scene.layers[0].set_effect('dropshadow')
circle = scene.layers[0].add_circle(
    radius=30,
    pos=(400, 300),
    color='red',
)

@w2d.event
def on_mouse_move(pos):
    circle.pos = pos

w2d.run()
```

![Output of the above program](https://github.com/lordmauve/wasabi2d/raw/master/docs/2020-01-10-screenshot.png)


## Installation


Use pip to install Wasabi2d from PyPI:

```
pip install wasabi2d
```

Please make sure your `requirements.txt` pins a major version, as Wasabi2D may
continue to make breaking API and graphical changes in major versions.


## Documentation

Documentation is available at https://wasabi2d.readthedocs.io/


## Screenshots

This screenshot shows off polygons, sprites, text and particle effects:

![Screenshot as of Wasabi2d 1.0.0](https://github.com/lordmauve/wasabi2d/raw/master/docs/2019-09-21-screenshot.png)

[Roller Knight](https://pyweek.org/e/wasabi28) was an entry in PyWeek 28, written with Wasabi2D by Daniel Pope and Larry Hastings:

![Roller Knight screenshot](https://github.com/lordmauve/wasabi2d/raw/master/docs/roller-knight.png)

[Spire of Chaos](https://pyweek.org/e/blaze/) was another entry in PyWeek 28 written with Wasabi2D by Daniel Moisset:

![Spire of Chaos screenshot](https://github.com/lordmauve/wasabi2d/raw/master/docs/spire-of-chaos.png)
