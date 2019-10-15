Animations
==========

You can animate arbitrary objects using the function ``wasabi2d.animate()``.
For example, to move a primitive from its current position on the
screen to the position ``(100, 100)``::

    animate(alien, pos=(100, 100))


.. function:: animate(object, tween='linear', duration=1, on_finished=None, **targets)

    Animate the attributes on object from their current value to that
    specified in the targets keywords.

    :param tween: The type of *tweening* to use.
    :param duration: The duration of the animation, in seconds.
    :param on_finished: Function called when the animation finishes.
    :param targets: The target values for the attributes to animate.

The tween argument can be one of the following:

+--------------------+------------------------------------------------------+-----------------------------------------------+
| 'linear'           | Animate at a constant speed from start to finish     | .. image:: _static/tween/linear.png           |
+--------------------+------------------------------------------------------+-----------------------------------------------+
| 'accelerate'       | Start slower and accelerate to finish                | .. image:: _static/tween/accelerate.png       |
+--------------------+------------------------------------------------------+-----------------------------------------------+
| 'decelerate'       | Start fast and decelerate to finish                  | .. image:: _static/tween/decelerate.png       |
+--------------------+------------------------------------------------------+-----------------------------------------------+
| 'accel_decel'      | Accelerate to mid point and decelerate to finish     | .. image:: _static/tween/accel_decel.png      |
+--------------------+------------------------------------------------------+-----------------------------------------------+
| 'in_elastic'       | Give a little wobble at the end                      | .. image:: _static/tween/in_elastic.png       |
+--------------------+------------------------------------------------------+-----------------------------------------------+
| 'out_elastic'      | Have a little wobble at the start                    | .. image:: _static/tween/out_elastic.png      |
+--------------------+------------------------------------------------------+-----------------------------------------------+
| 'in_out_elastic'   | Have a wobble at both ends                           | .. image:: _static/tween/in_out_elastic.png   |
+--------------------+------------------------------------------------------+-----------------------------------------------+
| 'bounce_end'       | Accelerate to the finish and bounce there            | .. image:: _static/tween/bounce_end.png       |
+--------------------+------------------------------------------------------+-----------------------------------------------+
| 'bounce_start'     | Bounce at the start                                  | .. image:: _static/tween/bounce_start.png     |
+--------------------+------------------------------------------------------+-----------------------------------------------+
| 'bounce_start_end' | Bounce at both ends                                  | .. image:: _static/tween/bounce_start_end.png |
+--------------------+------------------------------------------------------+-----------------------------------------------+

The ``animate()`` function returns an ``Animation`` instance:

.. class:: Animation

    .. method:: stop(complete=False)

        Stop the animation, optionally completing the transition to the final
        property values.

        :param complete: Set the animated attribute to the target value.

    .. attribute:: running

        This will be True if the animation is running. It will be False
        when the duration has run or the ``stop()`` method was called before
        then.

    .. attribute:: on_finished

        You may set this attribute to a function which will be called
        when the animation duration runs out. The ``on_finished`` argument
        to ``animate()`` also sets this attribute. It is not called when
        ``stop()`` is called. This function takes no arguments.
