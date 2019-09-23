# Wasabi 2D

A fledgling 2D graphics engine for Python, based on [moderngl], with
[pygame 2.0] for some supporting functions.

![Screenshot as of Wasabi2d 1.0.0](https://github.com/lordmauve/wasabi2d/raw/master/docs/2019-09-21-screenshot.png)


[moderngl]: https://github.com/moderngl/moderngl
[pygame 2.0]: https://www.pygame.org/news


Current features include:

* Sprite loading and rendering
* Rendering of text labels
* Stroked and solid-filled polygons, circles, stars, and rectangles
* Rotate, scale and move any of the above
* [Particle systems](https://wasabi2d.readthedocs.io/en/latest/particles.html)
* [Built-in post-processing effects](https://wasabi2d.readthedocs.io/en/latest/effects.html) using GLSL shaders.
* Sounds, keyboard and mouse events, animation/tweening, music, clocks and
  local storage
  from [Pygame Zero](https://pygame-zero.readthedocs.io/en/stable/index.html)
  (with most magic removed).

## Installation


Use pip to install Wasabi2d from PyPI:

```
pip install wasabi2d
```

Please make sure your `requirements.txt` pins a major version, as Wasabi2D may
continue to make breaking API and graphical changes in major versions.


## Documentation

Documentation is available at https://wasabi2d.readthedocs.io/
