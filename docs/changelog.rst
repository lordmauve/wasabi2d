History
=======

1.3.0 - unreleased
------------------

* New: add a :doc:`coroutine system <coros>`
* New: make F12 :ref:`a built-in combination <screenshot>` for
  screenshots/video recording.
* New: add a ``pixellate`` :doc:`post-processing effect <effects>`.
* Fix: add missing documentation for ``Layer.add_line()``
* Fix: grow a single texture atlas rather than allocating multiple. This
  removes a limit on how many unique text characters can be drawn with a single
  font.
* New: HeadlessScene class to run the graphics engine without creating a
  window.


1.2.0 - 2019-09-29
------------------

* New: add_sprite() takes an argument ``color`` to match other primitives
* New: ``.scale_x`` and ``.scale_y`` for independently scaling primitives
* New: ``scene.background`` can now be assigned as a color name
* Fix: pick suitable OpenGL version on OS X
* Fix: ``dropshadow`` effect is composited more correctly
* Fix: several bugs when resizing vertex/index buffers
* Fix: ``keymods`` is now exported from wasabi2d as documented.
* Fix: video recording is glitchy due to recording from back buffer
* Fix: text labels can now be empty
* Fix: text labels can be deleted
* Fix: particles display upside down and with rotation reversed


1.1.0 - 2019-09-22
------------------

* New: ``dropshadow`` :doc:`effect <effects>`.
* New: Particle group has ``spin_drag``.
* New: Particles can be emitted with ``angle`` and ``angle_spread``.


1.0.0 - 2019-09-21
------------------

* Initial PyPI version of Wasabi2D.
