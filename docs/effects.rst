Post-processing effects
=======================

Wasabi2d provides a small number of pre-defined full-screen post processing
effects. These are defined at the layer level, and affect items in that layer
only.

The effects are described here as separate calls:


.. method:: Layer.set_effect('bloom', radius: int=...)

    Create a light bloom effect, where very bright pixels glow, making them
    look exceptionally bright. The radius controls how far the effect reaches.


.. method:: Layer.set_effect('trails', fade: int=0.1)

    Apply a "motion blur" effect. Fade is the fraction of the full brightness
    that is visible after 1 second.

.. method:: Layer.clear_effect()

    Remove the active effect.

