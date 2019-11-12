Post-processing effects
=======================

Wasabi2d provides a small number of pre-defined full-screen post processing
effects. These are defined at the layer level, and affect items in that layer
only.

.. method:: Layer.set_effect(name, **kwargs)

    Set the effect for the layer to the given name. Return an object that
    can be used to set the parameters of the effect.

.. method:: Layer.clear_effect()

    Remove the active effect.

Available effects
-----------------

The effects are described here as separate calls:


.. method:: Layer.set_effect('bloom', radius: float=10)

    Create a light bloom effect, where very bright pixels glow, making them
    look exceptionally bright. The radius controls how far the effect reaches.

    .. image:: _static/effects/bloom.png
        :alt: Example of the light bloom effect


.. method:: Layer.set_effect('trails', fade: float=0.9, alpha: float = 1.0)

    Apply a "motion blur" effect. Fade is the fraction of the full brightness
    that is visible after 1 second.

    Alpha is the overall intensity of the effect.

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


.. method:: Layer.set_effect('pixellate', pxsize: int=10, antialias: float=1.0)

    Pixellate the contents of the layer. ``pxsize`` is the output pixel size.

    By default, this effect computes the average value within each pixel, ie.
    antialiases as it downsamples.

    For a more retro look, disable the antialiasing by passing ``antialias=0``.
    Values between 0 and 1 will give a weaker antialiasing effect; values
    greater than 1 give an even more blurred look.

    The effect runs on the GPU but with antialiasing, larger pxsizes are more
    costly to compute. The cost of the effect is *O(pxsize * antialias)*.

    .. versionadded:: 1.3.0

    .. image:: _static/effects/pixellate.png
        :alt: Example of the pixellate effect, with antialiasing on and off


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


.. method:: Layer.set_effect('greyscale', amount: float=1.0)

    Convert colours to greyscale or partially desaturate them.

    :param amount: The fraction of the colour to remove; 0.0 means keep full
                   colour, while 1.0 is fully black and white.

    .. versionadded:: 1.3.0

    .. image:: _static/effects/greyscale.png
        :alt: Examples of the greyscale effect


.. method:: Layer.set_effect('sepia', amount: float=1.0)

    Convert colours to sepia.

    Sepia is similar to greyscale effect in that it desaturates, but the sepia
    spectrum is slightly warmer, like an old photograph.

    :param amount: The fraction of the colour to remove; 0.0 means keep full
                   colour, while 1.0 is fully sepia.

    .. versionadded:: 1.3.0

    .. image:: _static/effects/sepia.png
        :alt: Examples of the sepia effect


.. method:: Layer.set_effect('posterize', levels: int=2, gamma: float=0.7)

    Map colours to a reduced palette.

    ``levels`` specifies the number of levels in each channel to reduce to
    (plus 0); the total number of colours will be ``levels ** 3``. For example,
    with ``levels=2`` the colours will be black, red, green, blue, yellow,
    cyan, magenta and white.

    ``gamma`` deserves particular attention. ``gamma`` is applied when
    calculating how the levels fall in the ``[0, 1]`` interval. When
    ``gamma=1``, levels will fall at regular intervals. Gamma less than 1
    dedicates more bands to dark colours, and few bands to light colours;
    gamma greater than 1 dedicates more bands to light colours, and more to
    dark colours. The overall brightness of the image does not change so much,
    but these can give very different effects, perhaps suiting different
    graphic styles.

    :param levels: The number of levels in each channel.
    :param gamma: A power expressing the spacing of the levels.

    .. versionadded:: 1.3.0

    .. image:: _static/effects/posterize.png
        :alt: Examples of the posterize effect


.. tip:: Effects Examples

    Each effect has an interactive example in the ``examples/effects/``
    directory in the `wasabi2d repository`__.

    Try cloning this repository and running the examples in order to better
    understand the effects.

.. __: https://github.com/lordmauve/wasabi2d/tree/master/examples/effects
