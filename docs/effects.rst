Post-processing effects
=======================

Wasabi2d provides a small number of pre-defined full-screen post processing
effects. These are defined at the layer level, and affect items in that layer
only.

The effects are described here as separate calls:


.. method:: Layer.set_effect('bloom', radius: float=10)

    Create a light bloom effect, where very bright pixels glow, making them
    look exceptionally bright. The radius controls how far the effect reaches.

    .. image:: _static/effects/bloom.png
        :alt: Example of the light bloom effect


.. method:: Layer.set_effect('trails', fade: float=0.1)

    Apply a "motion blur" effect. Fade is the fraction of the full brightness
    that is visible after 1 second.

    .. image:: _static/effects/trails.png
        :alt: Example of the trails effect

.. method:: Layer.clear_effect()

    Remove the active effect.

