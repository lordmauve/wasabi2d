.. _data_storage:


Data Storage
------------

The ``storage`` object behaves just like a Python dictionary but its contents
are preserved across game sessions. The values you assign to storage will be
saved as JSON_, which means you can only store certain types of objects in it:
``list``/``tuple``, ``dict``, ``str``, ``float``/``int``, ``bool``, and
``None``.

.. _JSON: https://en.wikipedia.org/wiki/JSON

The ``storage`` for a game is initially empty. Your code will need to handle
the case that values are loaded as well as the case that no values are found.

A tip is to use ``setdefault()``, which inserts a default if there is no value
for the key, but does nothing if there is.

For example, we could write::

    storage.setdefault('highscore', 0)

After this line is executed, ``storage['highscore']`` will contain a value -
``0`` if there was no value loaded, or the loaded value otherwise. You could
add all of your ``setdefault`` lines towards the top of your game, before
anything else looks at ``storage``::

    storage.setdefault('level', 1)
    storage.setdefault('player_name', 'Anonymous')
    storage.setdefault('inventory', [])

Now, during gameplay we can update some values::

    if player.colliderect(mushroom):
        score += 5
        if score > storage['highscore']:
            storage['highscore'] = score

You can read them back at any time::

    def draw():
        ...
        screen.draw.text('Highscore: ' + storage['highscore'], ...)

...and of course, they'll be preserved when the game next launches.

These are some of the most useful methods of ``storage``:

.. class:: Storage(dict)

    .. method:: storage[key] = value

        Set a value in the storage.

    .. method:: storage[key]

        Get a value from the storage. Raise KeyError if there is no such key
        in the storage.

    .. method:: setdefault(key, default)

        Insert a default value into the storage, only if no value already
        exists for this key.

    .. method:: get(key, default=None)

        Get a value from the storage. If there is no such key, return default,
        or None if no default was given.

    .. method:: clear()

        Remove all stored values. Use this if you get into a bad state.

    .. method:: save()

        Saves the data to disk now. You don't usually need to call this, unless
        you're planning on using ``load()`` to reload a checkpoint, for
        example.

    .. method:: load()

        Reload the contents of the storage with data from the save file. This
        will replace any existing data in the storage.

    .. attribute:: path

        The actual path to which the save data will be written.


.. caution::

    As you make changes to your game, ``storage`` could contain values that
    don't work with your current code. You can either check for this, or call
    ``.clear()`` to remove all old values, or delete the save game file.


.. tip::

    Remember to check that your game still works if the storage is empty!


