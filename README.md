# ![Wasabi 2D](https://raw.githubusercontent.com/lordmauve/wasabi2d/master/docs/_static/wasabi2d.png)

![PyPI](https://img.shields.io/pypi/v/wasabi2d) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wasabi2d) ![PyPI - Wheel](https://img.shields.io/pypi/wheel/wasabi2d)

[![Discord](https://img.shields.io/discord/705530610847973407)](https://discord.gg/jBWaWHU)

A fast, cutting-edge 2D game engine for Python.

Current features include:

* Sprites, text, and stroked and filled polygons - all rotatable, scalable, and
  colorizeable
* A [coroutine programming model](https://wasabi2d.readthedocs.io/en/latest/coros.html) for easy animated effects.
* [Particle systems](https://wasabi2d.readthedocs.io/en/latest/particles.html)
* [Built-in post-processing effects](https://wasabi2d.readthedocs.io/en/latest/effects.html) using GLSL shaders.
* [Sound, music and tone generation](https://wasabi2d.readthedocs.io/en/latest/sound.html).
* [Event driven input handling](https://wasabi2d.readthedocs.io/en/latest/events.html) for keyboard and mouse.
* [Animation/tweening](https://wasabi2d.readthedocs.io/en/latest/animation.html).
* ["Local storage"](https://wasabi2d.readthedocs.io/en/latest/storage.html) to easily save state.

Wasabi2D is based on [moderngl](supports OpenGL 4.1+), with [pygame 2.0] for some supporting functions, and supporting APIs ported from [Pygame Zero](https://github.com/lordmauve/pgzero).



[moderngl]: https://github.com/moderngl/moderngl
[pygame 2.0]: https://www.pygame.org/news

## Docs and Help

Documentation is available at https://wasabi2d.readthedocs.io/

Join us on [Discord for help and announcements!](https://discord.gg/jBWaWHU)


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


## Screenshots

This screenshot shows off polygons, sprites, text and particle effects:

![Screenshot as of Wasabi2d 1.0.0](https://github.com/lordmauve/wasabi2d/raw/master/docs/2019-09-21-screenshot.png)

[Roller Knight](https://pyweek.org/e/wasabi28) was an entry in PyWeek 28, written with Wasabi2D by Daniel Pope and Larry Hastings:

![Roller Knight screenshot](https://github.com/lordmauve/wasabi2d/raw/master/docs/roller-knight.png)

[Spire of Chaos](https://pyweek.org/e/blaze/) was another entry in PyWeek 28 written with Wasabi2D by Daniel Moisset:

![Spire of Chaos screenshot](https://github.com/lordmauve/wasabi2d/raw/master/docs/spire-of-chaos.png)

## Development and releases

Use Python 3.12 or later for the development and documentation tools:

```sh
uv venv
uv pip install -e . -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/sphinx-build -b html docs docs/_build/html
uv build
```

Git tags are the source of version numbers. `uv build` invokes `flit_scm`, which
uses `setuptools_scm` to generate `wasabi2d/__version__.py`; do not edit or commit
that generated file. Reinstall the editable package after switching revisions to
refresh it. The wheel and Sphinx docs use the same version metadata. Building
from an sdist also works without Git.

To release, publish a GitHub Release with a new PEP 440 version tag targeting
`master` (for example, `v1.5.0a2` or `v1.5.0`). Mark alpha, beta, release candidate,
and development releases as prereleases. For development tags use `.dev0`, which
allows setuptools_scm to number subsequent commits. Write the release notes in
GitHub; the Sphinx changelog reads them automatically. A pushed version tag also
runs the release workflow.

The Release workflow builds and validates the distributions before publishing
them to PyPI. Configure either a `PYPI_TOKEN` repository secret containing a
project-scoped PyPI API token, or a PyPI trusted publisher for owner `lordmauve`,
repository `wasabi2d`, workflow `release.yml` (no environment). Failed uploads can
be retried using **Run workflow** with the existing tag; already uploaded files
are skipped. Never move a published tag.

The **Backfill releases** workflow creates only missing historical GitHub
Releases, using `.github/release-history.json`, and creates the development test
release. It does not republish historical versions to PyPI. Their release notes
retain the original PyPI dates because GitHub's publication dates cannot be
backdated.

Public documentation builds can read the changelog anonymously. To avoid GitHub
API rate limits, set `SPHINX_GITHUB_CHANGELOG_TOKEN` in the documentation build
environment; Actions supplies its token automatically.
