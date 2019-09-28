History
=======


1.2.0 - 2019-09-29
------------------

* New: add_sprite() takes an argument ``color`` to match other primitives
* New: ``.scale_x`` and ``.scale_y`` for independently scaling primitives
* New: ``scene.background`` can now be assigned as a color name
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
