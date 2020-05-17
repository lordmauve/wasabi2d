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
* However the map can use at most 255 tile images. (To use more tiles, consider
  using multiple maps.)


Create a tile map in a layer by calling ``add_tile_map()``. The easiest form of
this requires no arguments. Setting tiles into the map is done by assigning the
name of an image (from the ``images/`` directory) to a coordinate pair:

.. code-block:: python

    tiles = scene.layers[3].add_tile_map()
    tiles[3, 5] = 'tile_sand'


.. method:: Layer.add_tile_map(*, tile_size: Tuple[int, int] = None, any_size_tile: bool = False) -> TileMap

    Create a tile map, initially blank.

    :param tile_size: The dimensions of each tile. If omitted this will be
                      inferred from the first tile you insert into the map.
    :param any_size_tile: If True, allow setting images of any size into the
                          map; otherwise, all tiles must match `tile_size`.
                          If this is given then `tile_size` is a required
                          parameter.


As well as setting tiles, there are a range of operations to treat the map as a
mapping of coordinate to image name. For example, you can retrieve the tile
values you have already set:

.. code-block:: python

    print(tiles[3, 5])  # prints tile_sand

There are also a number of :ref:`tile-drawing` operations to update the map
in bulk.


Tile Get/Set Operations
-----------------------

.. currentmodule:: wasabi2d.primitives.tile_map

.. automethod:: TileMap.__setitem__

.. automethod:: TileMap.__getitem__

.. automethod:: TileMap.get

.. automethod:: TileMap.setdefault

.. automethod:: TileMap.__delitem__

.. automethod:: TileMap.clear


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

You can also pass ``value=None`` in order to clear affected tiles.


.. automethod:: wasabi2d.primitives.tile_map.TileMap.fill_rect

.. automethod:: wasabi2d.primitives.tile_map.TileMap.line

.. automethod:: wasabi2d.primitives.tile_map.TileMap.flood_fill
