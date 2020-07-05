Groups
======

.. currentmodule:: wasabi2d

Groups make it easy to transform a collection of primitives, possibly in
different layers, as one unit.

For example, we could compose multiple sprites to make up the player's ship.
This lets us transform the ship together but apply effects such as changing the
ship's exhaust colour without affecting the fuselage::

    ship = wasabi2d.Group([
        scene.layers[0].add_sprite('ship'),
        scene.layers[1].add_sprite('ship_exhaust', pos=(-10, 0))
    ])

    ship.pos = 500, 300
    ship.scale = 2

When an object is in a group, you can still update its properties individually::

    # make the exhaust colour transparent
    ship[1].color = (1.0, 1.0, 1.0, 0.5)

    # make the exhaust flame move backwards
    animate(ship[1], pos=(-20, 0))

...but the transformation properties apply relative to the group itself. So the
animation above will play even as the ship moves around - perhaps under player
control.

Essentially, a group is a separate
:ref:`local coordinate system <group-coordinates>` for the objects it contains.

Constructing a Group
--------------------

.. autoclass:: Group

    Construct a group by giving it a list of the primitives it should contain.

    The list may be empty.

    Each primitive may be at most one group. Often a primitive will be
    associated with a group for its whole life. Deleting a group with
    :meth:`delete()` deletes all the objects it contains.


.. _group-coordinates:

Group coordinates
-----------------

A group has its local coordinate system. It's handy to be able to convert
positions between group coordinates and world coordinates:

.. automethod:: Group.local_to_world

.. automethod:: Group.world_to_local


Sometimes you just want to transform a vector, such as a velocity, rather than
a position. The transformation is slightly different because it doesn't take
into account the *position* of the group - only its scale/angle:

.. automethod:: Group.localvec_to_worldvec

.. automethod:: Group.worldvec_to_localvec


For example, we could get the velocity of a bullet shot by a ship::

    SHOOT_VELOCITY = 200, 0
    bullet_velocity = ship.localvec_to_worldvec(SHOOT_VELOCITY)


.. _group-capture:

Moving things in and out of Groups
----------------------------------

There are two ways of moving objects in and out of groups, and you might need
both of them. Assuming the group is already transformed, the two ways are:

1. Keep the object's ``angle``, ``scale``, ``pos`` values, exactly as they are,
   but reinterpret them as relative to the group. This means that the object
   moves.
2. Keep the object where it is, but update ``angle``, ``scale`` and ``pos``.
   This means that the object doesn't move.

When items are added in the constructor, or :meth:`.extend()`,
:meth:`.append()`, they are directly specified in the group's local coordinate
system - this is method 1 above.

For method 2 - to keep the object where it is - Wasabi2D provides a separate
set of methods. You can move one object in and out of a group, move out all
of the objects, or build a group by moving in objects already in the scene.


.. automethod:: Group.pop

.. automethod:: Group.capture

.. automethod:: Group.explode

.. automethod:: Group.from_objects

.. note::

   In Wasabi2D we don't support *skew* for primitives, which means that if the
   group has a different value for ``scale_x`` and ``scale_y``, then the
   primitive will appear differently after this operation. It should still have
   the same position, angle, and scale, but it will acquire/lose skew.


Groups as a list of objects
---------------------------

To work with the items in a group you can simply treat the group like a list of
objects::

    group = Group([
        scene.layers[0].add_sprite('ship'),
        scene.layers[1].add_sprite('ship_exhaust', pos=(-10, 0))
    ])

    print(len(group))  # count the items in a group
    ship, exhaust = group  # iterate over the items

    ship = group[0]  # get an item
    group[1] = scene.layers[1].add_sprite('ship_boost')  # replace
    del group[0]  # delete an item

You can add items to the group. Note that the transformation that you give for
the items is in group-local coordinates::

    # Add additional items to the group
    group.extend([
        scene.layers[0].add_sprite('mega_gun', pos=(-5, -10)),
        scene.layers[0].add_sprite('mega_gun', pos=(-5, 10)),
    ])

.. automethod:: Group.append
.. automethod:: Group.extend

Finally you can delete or clear the group, which removes all objects in the
group from the scene:

.. automethod:: Group.delete

.. automethod:: Group.clear

(To keep the objects in the scene, use :meth:`.explode()`.)
