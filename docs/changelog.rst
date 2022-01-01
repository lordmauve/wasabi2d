History
=======

1.5.0 - unreleased
------------------

* New: :ref:`Structured Concurrency model <sc>` for coroutines
* New: :ref:`subclocks` to allow for slow-motion effects and pausing
* New: :class:`wasabi2d.chain.Light`
* Fix: sprites do not update when only the image is changed.
* Fix: crash when deleting a text label
* Fix: crash when deleting a group

1.4.0 - 2020-07-09
------------------

* New: :doc:`Tile maps <tile_maps>`
* New: :doc:`Groups <groups>`
* New: :ref:`Emitter objects <emitters>`
* New: scene-wide :ref:`pixel_art mode <pixel-art>`
* New: vertices of a line can now be updated
* New: `background=` can be set in Scene constructor
* New: `label.text` can be assigned a non-str
* Fix: bug with drawing end segments of lines and lines at right angles
* Fix: `stroke_width` wasn't passed through in `add_rect`
* Fix: Use NFC not NFKC for Unicode normalisation


1.3.0 - 2019-12-10
------------------

* New: add a :doc:`coroutine system <coros>`
* New: make F12 :ref:`a built-in combination <screenshot>` for
  screenshots/video recording.
* New: :ref:`chain`, for more powerful post-processing effect
  configurations
* New: ``Mask`` chain effect.
* New: ``DisplacementMap`` chain effect.
* New: ``trails`` effect takes an ``alpha`` parameter
* New: ``bloom`` effects takes ``gamma`` and ``intensity`` parameters
* New: shape primitives are drawn with antialiasing
* New: tone generation supports square and saw waves
* New: add ``pixellate``, ``greyscale``, ``sepia`` and ``posterize``
  :doc:`post-processing effects <effects>`.
* New: :ref:`scene-scaling` for high dpi displays and retro games
* New: Sprites now support ``.anchor_x`` and ``.anchor_y``
  parameters/attributes
* Fix: actually release OpenGL resources, which needed to be done explicitly
* Fix: add missing documentation for ``Layer.add_line()``
* Fix: grow a single texture atlas rather than allocating multiple. This
  removes a limit on how many unique text characters can be drawn with a single
  font.
* Fix: crash when creating a scene from a REPL
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
