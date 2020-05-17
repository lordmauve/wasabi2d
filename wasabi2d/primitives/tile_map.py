"""Sparse tile maps."""
import random
from itertools import product
from typing import Tuple, Dict, Set, Optional, List, TypeVar, Union
from collections import deque

import moderngl
import numpy as np
import bresenham

import wasabi2d
from ..allocators.abstract import FreeListAllocator, NoCapacity
from ..allocators.vertlists import dtype_to_moderngl


def grow(arr: np.ndarray, newsize: int) -> np.ndarray:
    shape = list(arr.shape)
    shape[0] = newsize

    new = np.empty_like(arr, shape=shape)
    new[:len(arr)] = arr
    return new


T = TypeVar('T')


class TileManager:
    """Manage tile blocks in a texture and a vertex buffer enumerating them.

    Each vertex buffer entry will contain the block coordinates for the block
    and the location in the texture where the texture data is found. This
    latter location is stored as an integer index.

    Each texture block will be a 64x64 region of uint8 tile values.

    """
    ctx: moderngl.Context

    # Allocator for texture areas
    alloc: FreeListAllocator
    texture: moderngl.Texture

    # Vertices and a backing memory array
    verts: moderngl.Buffer
    vertdata: np.ndarray
    verts_dirty: bool = True

    block_map: Dict[Tuple[int, int], int]
    texture_blocks: Dict[int, np.ndarray]
    dirty_blocks: Set[int]

    NP_DTYPE = np.dtype([
        ('in_vert', '2i4'),
        ('in_tilemap_block', 'u2'),
    ])
    MGL_DTYPE = dtype_to_moderngl(NP_DTYPE)

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx

        # TODO: this allocator is overkill given that we cannot actually
        # free tile blocks individually; replace with a simple counter
        self.alloc = FreeListAllocator()
        self.block_map = {}
        self.dirty_blocks = set()
        self.texture_blocks = {}

        self.mktex(self.alloc.capacity)
        self.vertdata = np.empty(self.alloc.capacity, dtype=self.NP_DTYPE)
        self.verts = self.ctx.buffer(self.vertdata)

    def mktex(self, capacity: int):
        """Create a new texture."""
        self.texture = self.ctx.texture(
            (capacity * 64, 64), 1,
            dtype='f1'
        )

    def mktile(self) -> np.ndarray:
        """Create a tile in memory."""
        return np.zeros((64, 64), dtype=np.uint8)

    def _resize(self, new_capacity: int):
        """Resize to hold new_capacity tiles."""
        self.texture.release()
        self.mktex(new_capacity)
        self.alloc.grow(new_capacity)
        self.dirty_blocks.update(self.block_map.values())
        self.vertdata = grow(self.vertdata, new_capacity)
        self.verts.orphan(new_capacity)
        self.verts_dirty = True

    def release(self):
        """Release the ModernGL objects."""
        if self.verts:
            self.verts.release()
            self.verts = None
        if self.texture:
            self.texture.release()
            self.texture = None

    def __del__(self):
        self.release()

    def create_block(self, pos: Tuple[int, int]) -> np.ndarray:
        try:
            tile_id = self.alloc.alloc()
        except NoCapacity as e:
            self.resize(e.capacity)
            tile_id = self.alloc.alloc()

        vert_id = len(self.block_map)

        tile = self.mktile()
        self.block_map[pos] = tile_id
        self.texture_blocks[tile_id] = tile
        self.dirty_blocks.add(tile_id)

        self.vertdata[vert_id] = pos, tile_id

        stride = self.vertdata.strides[0]
        self.verts.write(
            data=self.vertdata[vert_id:vert_id + 1],
            offset=stride * vert_id
        )
        return tile

    def clear(self):
        """Clear all allocations."""
        self.alloc = FreeListAllocator(self.alloc.capacity)
        self.block_map.clear()
        self.texture_blocks.clear()
        self.dirty_blocks.clear()

    def __len__(self):
        return len(self.block_map)

    def get_or_create_block(self, pos: Tuple[int, int]) -> np.ndarray:
        """Get or create the block for the given coordinates.

        This method is intended for updates to the block and will mark the
        block as dirty.

        """
        id = self.block_map.get(pos)
        if id is None:
            return self.create_block(pos)
        self.dirty_blocks.add(id)
        return self.texture_blocks[id]

    def get_block(self, pos: Tuple[int, int]) -> Optional[np.ndarray]:
        """Retrieve the block with the given coordinates if it exists.

        This method does not mark the block as dirty.
        """
        id = self.block_map.get(pos)
        if id is None:
            return None
        return self.texture_blocks[id]

    def touch_block(self, pos: Tuple[int, int]):
        """Mark a block as dirty."""
        self.dirty_blocks.append(self.block_map[pos])

    def bind_texture(self, unit: int):
        """Bind the texture to a texture unit."""
        for tile_id in self.dirty_blocks:
            tile = self.texture_blocks[tile_id]
            self.texture.write(
                tile,
                (tile_id * 64, 0, 64, 64),
                alignment=1
            )
        self.dirty_blocks.clear()
        self.texture.use(unit)


class TileMap:
    """A sparse tile map."""
    _tiles: List[str]
    layer: 'wasabi2d.layers.Layer'
    _tilemgr: TileManager

    # A texture holding texture coordinates for tiles in the map,
    # and its backing store in memory.
    _tile_tex: moderngl.Texture = None
    _texdata: np.ndarray
    _tile_tex_dirty: bool = False

    vao: moderngl.VertexArray = None

    size: Optional[Tuple[int, int]] = None
    tex: Optional = None
    block_size: Optional[Tuple[int, int]] = None

    def __init__(self, layer, *, tile_size=None, any_size_tile=False):
        super().__init__()
        self.layer = layer
        self.atlas = self.layer.group.atlas
        self._tiles = [None]

        if tile_size:
            w, h = self.size = tile_size
            self.block_size = w * 64, h * 64
        if any_size_tile and not tile_size:
            raise ValueError(
                "tile_size must be given to use any_size_tile"
            )
        self.any_size_tile = any_size_tile

        self._texdata = np.zeros((256, 4, 2), dtype=np.float32)
        self._names = {}
        self._tile_tex = self.layer.ctx.texture(
            (2, 256),
            4,
            dtype='f4'
        )
        self._tile_tex.filter = moderngl.NEAREST, moderngl.NEAREST

        self._tilemgr = TileManager(self.layer.ctx)

        shadermgr = layer.group.shadermgr

        self.prog = shadermgr.load('primitives/tile_map')
        self.vao = self.layer.ctx.vertex_array(
            self.prog,
            [(self._tilemgr.verts, *TileManager.MGL_DTYPE)]
        )
        layer.arrays[id(self)] = self

    def release(self):
        """Release OpenGL resources associated with this TileMap."""
        if self.vao:
            self.vao.release()
        if self._tile_tex:
            self._tile_tex.release()
        if self._tilemgr:
            self._tilemgr.release()
        self._tilemgr = self._tile_tex = self.vao = None

    def __del__(self):
        self.release()

    def _map_name(self, name: str) -> int:
        """Given an image name, return an integer mapping for it.

        If the image is not already in the tile list, assign it a new ID.
        """
        if name is None:
            return 0
        try:
            return self._names[name]
        except KeyError:
            pass

        id = len(self._tiles)

        region = self.atlas.get(name)
        rsize = region.width, region.height
        if id >= 256:
            raise ValueError(
                f"Cannot insert {name} to {self!r}; "
                "{len(self._tiles)} tile slots are already in use."
            )
        if id > 1:
            if rsize != self.size and not self.any_size_tile:
                raise ValueError(
                    f"Size of {name} ({rsize}) does not match "
                    f"previous tiles {self.size}"
                )
            if region.tex is not self.tex:
                raise ValueError(
                    f"Tile size is too large {rsize}"
                )
        else:
            self.tex = region.tex
            if not self.size:
                self.size = rsize
                self.block_size = region.width * 64, region.height * 64

        tl, tr, br, bl = region.texcoords.astype(np.float32)

        self._texdata[id, :] = [tl, tr - tl, bl - tl, (0, 0)]
        self._tile_tex_dirty = True
        self._tiles.append(name)
        self._names[name] = id
        return id

    def _value_gen(self, value):
        """Return a generator for tile values."""
        if value is None or isinstance(value, str):
            id = self._map_name(value)
            while True:
                yield id

        choices = [self._map_name(v) for v in value]
        while True:
            yield random.choice(choices)

    def fill_rect(
        self,
        value: Union[str, List[str], None],
        left: int,
        top: int,
        right: int,
        bottom: int,
    ):
        """Fill a rectangle of the tile map.

        `value` can be a string to fill with just one tile value or a list of
        strings in order to fill with one of a range of choices. You can also
        pass ``None`` in order to clear tiles instead of setting them.

        Note that right/bottom are exclusive.
        """
        cells = product(range(left, right), range(top, bottom))
        for pos, v in zip(cells, self._value_gen(value)):
            self._set(pos, v)

    def line(
        self,
        value: Union[str, List[str], None],
        start: Tuple[int, int],
        stop: Tuple[int, int],
    ):
        """Fill a line from coordinates start to stop.

        `value` can be a string to fill with just one tile value or a list of
        strings in order to fill with one of a range of choices. You can also
        pass ``None`` in order to clear tiles instead of setting them.

        """
        cells = bresenham.bresenham(*start, *stop)
        for pos, v in zip(cells, self._value_gen(value)):
            self._set(pos, v)

    def flood_fill(
        self,
        value: Union[str, List[str], None],
        start: Tuple[int, int],
        *,
        limit: int = 10_000
    ):
        """Flood fill from the given position.

        `value` can be a string to fill with just one tile value or a list of
        strings in order to fill with one of a range of choices. You can also
        pass ``None`` in order to clear tiles instead of setting them.

        Because the tile map is unbounded, `limit` caps the number of
        tiles that can be considered for filling. If this limit is hit
        then an exception is raised and no tiles are updated.

        """
        values = self._value_gen(value)
        match_value = self._get(start)
        queue = deque([start])
        seen = {start, }
        fill = []
        for _ in range(limit):
            if not queue:
                break
            pos = queue.popleft()
            if self._get(pos) != match_value:
                continue
            fill.append(pos)

            x, y = pos
            neighbours = {
                (x + 1, y),
                (x - 1, y),
                (x, y + 1),
                (x, y - 1),
            } - seen
            queue.extend(neighbours)
            seen.update(neighbours)
        else:
            raise ValueError(f"Hit flood-fill limit of {limit} tiles")
        for pos, v in zip(fill, values):
            self._set(pos, v)

    def __getitem__(self, pos: Tuple[int, int]) -> str:
        """Get the tile at the given position."""
        v = self.get(pos)
        if not v:
            raise KeyError(f"No tile at position {pos}")
        return v

    def get(self, pos: Tuple[int, int], default: T = None) -> Union[str, T]:
        """Get the tile at the given position.

        If there is no tile at that position, `default` is returned.
        """
        id = self._get(pos)
        if id == 0:
            return default
        return self._tiles[id]

    def _get(self, pos: Tuple[int, int]) -> int:
        """Get the tile id at the given position.

        If there is no tile at that position, 0 is returned.
        """
        cell, (x, y) = np.divmod(pos, 64)
        block = self._tilemgr.get_block(tuple(cell))
        return block is not None and block[y, x] or 0

    def __setitem__(self, pos: Tuple[int, int], value: str):
        """Set the tile at the given position."""
        id = self._map_name(value)
        self._set(pos, id)

    def _set(self, pos, tid: int):
        """Set a tile id at a given location."""
        cell, (x, y) = np.divmod(pos, 64)
        block = self._tilemgr.get_or_create_block(tuple(cell))
        block[y, x] = tid

    def setdefault(self, pos: Tuple[int, int], value: str) -> str:
        """Set a tile in the tile map if it is not set.

        Return the tile that is set in this cell after the call.
        """
        cell, (x, y) = np.divmod(pos, 64)
        block = self._tilemgr.get_or_create_block(tuple(cell))
        idx = y, x
        v = block[idx] = block[idx] or self._map_name(value)
        return self._tiles[v]

    def __delitem__(self, pos: Tuple[int, int]):
        """Clear the tile at the given position."""
        self._set(pos, 0)

    def clear(self):
        """Clear the tile map."""
        self._tilemgr.clear()
        self._tiles.clear()
        self._names.clear()

    @property
    def bounds(self):
        """todo"""
        raise NotImplementedError()

    def delete(self):
        """Delete this primitive."""
        self.layer._dirty.discard(self)
        self.layer.objects.discard(self)
        self.layer = None
        self.release()

    def render(self, camera: wasabi2d.scene.Camera):
        blocks = len(self._tilemgr.block_map)
        if not blocks:
            return
        self._tilemgr.bind_texture(0)
        self.prog['tiles'] = 0

        if self._tile_tex_dirty:
            self._tile_tex.write(self._texdata)
            self._tile_tex_dirty = False

        self._tile_tex.use(1)
        self.prog['tilemap_coords'] = 1

        self.tex.tex.use(2)
        self.prog['tex'] = 2
        self.prog['block_size'] = self.block_size
        self.prog['screen_width'] = camera.width

        self.vao.render(
            mode=moderngl.POINTS,
            vertices=blocks
        )
