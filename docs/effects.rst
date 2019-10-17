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


.. method:: Layer.set_effect('blur', radius: float=10.0)

    Apply a full screen gaussian blur.

    ``radius`` is the maximum radius of the blur.

    The effect runs on the GPU but larger radiuses are more costly to compute.
    The cost of the effect is *O(radius)*.

    .. image:: _static/effects/blur.png
        :alt: Example of the blur effect


.. method:: Layer.set_effect('pixellate', pxsize: int=10)

    Pixellate the contents of the layer. ``pxsize`` is the output pixel size.

    This effect computes the average value within each pixel, ie. antialiases
    as it downsamples.

    The effect runs on the GPU but larger pxsizes are more costly to compute.
    The cost of the effect is *O(pxsize)*.

    .. versionadded:: 1.3.0

    .. image:: _static/effects/pixellate.png
        :alt: Example of the pixellate effect


.. method:: Layer.set_effect('dropshadow', radius: float=10.0, opacity: float=1.0, offset: Tuple[float, float]=(1.0, 1.0))

    Apply a drop-shadow effect: draw an offset, blurred copy layer underneath
    the normal layer contents.

    :param radius: The maximum radius of the blur.
    :param opacity: The opacity of the shadow; 1.0 is black, lower values make
                    the shadow partially transparent.
    :param offset: The offset of the shadow in screen pixels. ``(1, 1)``
                   offsets the shadow downwards and to the right. Note that
                   this is a screen-space effect and these coordinates are
                   always in screen space.

    .. versionadded:: 1.1.0

    .. image:: _static/effects/dropshadow.png
        :alt: Example of the drop shadow effect


.. method:: Layer.clear_effect()

    Remove the active effect.

