# Wasabi 2D

A fast, cutting-edge 2D game engine for Python.

Current features include:

* Rotate, scale, move and colorize all primitives:
  * Sprites
  * Text labels
  * Stroked and solid-filled polygons, circles, stars, and rectangles
* A [coroutine programming model]() for easy animated effects.
* [Particle systems](https://wasabi2d.readthedocs.io/en/latest/coros.html)
* [Built-in post-processing effects](https://wasabi2d.readthedocs.io/en/latest/effects.html) using GLSL shaders.
* Sound, music and tone generation.
* Event driven input handling for keyboard and mouse.
* Animation/tweening.
* "Local storage" to easily save state.

Wasabi2D is based on [moderngl], with [pygame 2.0] for some supporting functions, and supporting APIs ported from [Pygame Zero](https://github.com/lordmauve/pgzero).

![Screenshot as of Wasabi2d 1.0.0](https://github.com/lordmauve/wasabi2d/raw/master/docs/2019-09-21-screenshot.png)


[moderngl]: https://github.com/moderngl/moderngl
[pygame 2.0]: https://www.pygame.org/news


## Installation


Use pip to install Wasabi2d from PyPI:

```
pip install wasabi2d
```

Please make sure your `requirements.txt` pins a major version, as Wasabi2D may
continue to make breaking API and graphical changes in major versions.


## Documentation

Documentation is available at https://wasabi2d.readthedocs.io/
