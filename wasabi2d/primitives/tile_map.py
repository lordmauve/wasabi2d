"""Sparse tile maps."""
import random
from itertools import product
from typing import Tuple, Dict, Set, Optional, List

import moderngl
import numpy as np

import wasabi2d
from ..allocators.abstract import FreeListAllocator, NoCapacity
from ..allocators.vertlists import dtype_to_moderngl


def grow(arr: np.ndarray, newsize: int) -> np.ndarray:
    shape = list(arr.shape)
    shape[0] = newsize

    new = np.empty_like(arr, shape=shape)
    new[:len(arr)] = arr
    return new


class TileManager:
    """Manage tile blocks in a texture and a vertex buffer enumerating them.

    Each vertex buffer entry will contain the block coordinates for the block
    and the location in the texture where the texture data is found. This
    latter location is stored as an integer index.

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
        self.verts.write(self.vertdata)  # TODO: write just this one

        return tile

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
        id = self.block_map[pos]
        if id is None:
            return None
        return self.texture_blocks[id]

    def touch_block(self, pos: Tuple[int, int]):
        """Mark a block as dirty."""
        self.dirty_blocks.append(self.block_map[pos])

    def bind_texture(self, unit: int):
        """Bind the texture to a texture unit."""

        def nonzeros(arr):
            w, h = arr.shape
            for x in range(w):
                for y in range(h):
                    v = arr[x, y]
                    if v != 0:
                        print((x, y), v)

        for tile_id in self.dirty_blocks:
            tile = self.texture_blocks[tile_id]
            nonzeros(tile)
            self.texture.write(
                tile,
                (tile_id * 64, 0, 64, 64),
                alignment=1
            )

            readback = np.frombuffer(
                self.texture.read(alignment=1),
                dtype=np.uint8
            ).reshape(512, 64)

            nonzeros(readback)
        self.dirty_blocks.clear()
        self.texture.use(unit)


class TileMap:
    """A sparse tile map."""
    _tiles: List[str]
    layer: 'wasabi2d.layers.Layer'
    _tilemgr: TileManager
    _tile_tex: moderngl.Texture = None
    vao: moderngl.VertexArray = None

    def __init__(self, layer, tiles: List[str]):
        super().__init__()
        self.layer = layer
        self._tiles = list(tiles)

        self._tilemgr = TileManager(self.layer.ctx)

        self._build_tiledata_texture()

        shadermgr = layer.group.shadermgr

        self.prog = shadermgr.load('tile_map')
        self.vao = self.layer.ctx.vertex_array(
            self.prog,
            [(self._tilemgr.verts, *TileManager.MGL_DTYPE)]
        )
        layer.arrays[id(self)] = self

    def release(self):
        if self.vao:
            self.vao.release()
        if self._tile_tex:
            self._tile_tex.release()
        if self._tilemgr:
            self._tilemgr.release()
        self._tilemgr = self._tile_tex = self.vao = None

    def __del__(self):
        self.release()

    def _build_tiledata_texture(self):
        """Build a texture of UV coordinates for our tile map."""
        if self._tile_tex:
            self._tile_tex.release()

        num = len(self._tiles)
        assert num > 0, \
            "No tiles provided."
        assert num <= 255, \
            "A maximum of 255 tiles are supported in one tile map."

        texdata = np.zeros((num, 4, 2), dtype=np.uint16)

        atlas = self.layer.group.atlas
        size = tex = None
        self._names = {}
        for i, t in enumerate(self._tiles):
            region = atlas.get(t)
            rsize = region.width, region.height
            if i > 0:
                if rsize != size:
                    raise ValueError(
                        f"Size of {t} rsize does not match "
                        f"previous tiles {size}"
                    )
                if region.tex is not tex:
                    raise ValueError(
                        f"Tile size is too large {rsize}"
                    )
            else:
                size = rsize
                tex = region.tex
            texdata[i, ...] = region.texcoords
            self._names[t] = i + 1
        self.tex = tex
        self.block_size = tuple(c * 64 for c in size)
        self._tile_tex = self.layer.ctx.texture(
            (4, num),
            2,
            data=texdata,
            dtype='u2'
        )
        self._tile_tex.filter = moderngl.NEAREST, moderngl.NEAREST

    def fill_rect(self, value, left, right, top, bottom):
        """Fill a rectangle of the tile map.

        Note that right/bottom are exclusive.
        """
        cells = product(range(left, right), range(top, bottom))
        if isinstance(value, str):
            value = self._names[value]

        if isinstance(value, int):
            for pos in cells:
                self[pos] = value
        else:
            # Map values to integers once
            value = [
                self._names[v] if isinstance(v, str) else int(v)
                for v in value
            ]
            for pos in cells:
                self[pos] = random.choice(value)

    def __getitem__(self, pos):
        x, y = pos
        cellx, x = divmod(x, 64)
        celly, y = divmod(y, 64)
        block = self._tilemgr.get_block(cellx, celly)
        return block[y, x]

    def __setitem__(self, pos, value):
        if isinstance(value, str):
            value = self._names[value]
        assert isinstance(value, int) and 0 <= value < 255
        x, y = pos
        cellx, x = divmod(x, 64)
        celly, y = divmod(y, 64)

        block = self._tilemgr.get_or_create_block((cellx, celly))
        block[y, x] = value

    @property
    def bounds(self):
        """todo"""
        raise NotImplementedError()

    def delete(self):
        """Delete this primitive."""
        self.layer._dirty.discard(self)
        self.layer.objects.discard(self)
        self.layer = None

    def render(self, camera: wasabi2d.scene.Camera):
        self._tilemgr.bind_texture(0)
        self.prog['tiles'] = 0

        self._tile_tex.use(1)
        self.prog['tilemap_coords'] = 1

        self.tex.tex.use(2)
        self.prog['tex'] = 2
        self.prog['block_size'] = self.block_size

        self.vao.render(
            mode=moderngl.POINTS,
            vertices=len(self._tilemgr)
        )
