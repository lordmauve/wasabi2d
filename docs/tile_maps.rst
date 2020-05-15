Tile Maps
=========

Many games use a rectangular grid of tile images to represent things like
background scenery.

You could use sprite primitives to do this, this is relatively expensive both
in terms of memory usage and rendering. Instead Wasabi2D provides a GPU
accelerated tile map that is fast to render even over vast tile maps.

Some of the properties of this tile map:

* You do not need to declare the bounds of the map. Maps do not have to
  have rectangular bounds or be contiguous.
* You can update tiles at any coordinate at any time.
* However the map can use at most 255 tile images. (To use more tiles, consider using multiple maps.)


Create a tile map in a layer by calling ``add_tile_map()``:

.. method:: Layer.add_tile_map() -> TileMap

    Create a tile map, initially blank.


This tile map will be blank - and lacking even dimensions - until you set tiles
into it.

Setting tiles into the map is done by assignment to coordinate pair:

.. code-block:: python

    tiles = scene.layers[3].add_tile_map()
    tiles[3, 5] = 'tile_sand'

There are also a number of :ref:`tile-drawing` operations to update the map
in bulk.


Tile Get/Set Operations
-----------------------

.. autoclass:: wasabi2d.primitives.tile_map.TileMap
    :members: __setitem__, __getitem__, get, setdefault, __delitem__


.. _tile-drawing:

Tile Drawing Operations
-----------------------

All these methods accept a tile parameter given as a string to set in the tile map.

They also accept a list of tile image names. In this case each tile that is
drawn randomly picks from the list::

    tiles = scene.layers[0].add_tile_map()
    tiles.line(
        ['fence1', 'fence2'],  # randomly pick fence tile images
        start=(0, 0),
        end=(20, 0),
    )


.. automethod:: wasabi2d.primitives.tile_map.TileMap.fill_rect

.. automethod:: wasabi2d.primitives.tile_map.TileMap.line

.. automethod:: wasabi2d.primitives.tile_map.TileMap.flood_fill
