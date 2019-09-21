Post-processing effects
=======================

Wasabi2d provides a small number of pre-defined full-screen post processing
effects. These are defined at the layer level, and affect items in that layer
only.

.. method:: Layer.set_effect(name, **kwargs)

    Set the effect for the layer to the given name. Return an object that
    can be used to set the parameters of the effect.


Available effects
-----------------

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


.. method:: Layer.set_effect('punch', factor: float=1.0)

    Apply a pinch/punch effect.

    A factor greater than 1.0 creates a "punch" effect; objects near the center
    of the camera are enlarged and objects at the edge are shrunk.

    A factor less than 1.0 creates a "pinch" effect; objects near the center of
    the camera are shrunk and objects at the edge are enlarged.

    .. image:: _static/effects/punch.png
        :alt: Example of the punch effect

    .. image:: _static/effects/pinch.png
        :alt: Example of the pinch effect


.. method:: Layer.clear_effect()

    Remove the active effect.

