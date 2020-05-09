"""Sparse tile maps."""
import numpy as np
import random
from itertools import product
from typing import Tuple

from .base import Colorable, Transformable
from ..allocators.vertlists import MemoryBackedBuffer, dtype_to_moderngl


TILES_PROGRAM = dict(
    vertex_shader='''
#version 330

in vec2 in_vert;
in ivec2 in_tilemap_blok;

void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
    ''',
    geometry_shader="""
in ivec2 in_uv;
out vec2 uv;
uniform sampler2D tile_coords;
uniform vec2 tile_size;

uniform mat4 proj;

const vec2 corners[4] = vec2[4](
    vec2(0.0, 0.0),
    vec2(0.0, 1.0),
    vec2(1.0, 0.0),
    vec2(1.0, 1.0),
);


/* Project a relative vector using the mvp matrix. */
vec2 project_vec(vec2 v) {
    return (proj * vec4(v, 0.0, 0.0)).xy;
}


/* Project a point using the mvp matrix. */
vec2 project_point(vec2 v) {
    return (proj * vec4(v, 0.0, 1.0)).xy;
}


void main() {
    vec4 point = gl_in[0].gl_Position;

    vec2 topleft = project_point(point.xy);
    vec2 tile_x = project_vec(vec2(tile_size.x, 0.0));
    vec2 tile_y = project_vec(vec2(0.0, tile_size.y));

    vec2 tile_across = tile_x + tile_y;

    // Cull
    vec4 xform_centre = topleft + tile_across * 4.0;
    float radius = length(tile_across);
    if (all(greaterThan(xform_centre, vec2(1.0 - radius, 1.0 - radius)))) {
        return;
    }

    mat2 tilespace = mat2(tile_x, tile_y);

    for (int y = 0; y < 8; y++) {
        for (int x = 0; x < 8; x++) {
            vec2 coord = vec2(x, y);
            for (int c = 0; c < 4; c++) {
                gl_Position = topleft + tilespace * (coord + corners[c]);
                EmitVertex();
            }
            EndPrimitive();
        }
    }
}
""",
    fragment_shader='''
#version 330

out vec4 f_color;
in vec2 uv;
uniform vec4 color;
uniform sampler2D tex;

void main() {
    f_color = color * texture(tex, uv);
}
''',
)


class TextureBlockManager:
    ctx: 'moderngl.Context'


class TileMap(Colorable):
    """A sparse tile map."""

    def __init__(self, layer, tiles):
        super().__init__()
        self.layer = layer
        self._tiles = list(tiles)
        self._tile_tex = None
        self._build_texture()
        self._build_buffer()

    def _build_texture(self):
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
            self._names[t] = i
        self._tile_tex = self.layer.ctx.texture(
            (num, 2),
            4,
            data=texdata,
            dtype='u2'
        )

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
        cellx, x = divmod(x, 8)
        celly, y = divmod(y, 8)
        index = self._allocations[cellx, celly]
        return self._data[index]['in_tiles'][x + y * 8]

    def __setitem__(self, pos, value):
        if isinstance(value, str):
            value = self._names[value]
        assert isinstance(value, int) and 0 <= value < 255
        x, y = pos
        cellx, x = divmod(x, 8)
        celly, y = divmod(y, 8)
        pos = cellx, celly
        index = self._allocations.get(pos)
        if index is None:
            index = self._allocate(pos)
        print(self._data.shape, self._data.dtype)
        self._data[index]['in_tiles'][x + y * 8] = value
        self._set_dirty()

    def __delitem__(self, pos):
        self[pos] = 256

    NP_DTYPE = np.dtype([
        ('in_vert', '2f4'),
        ('in_tilemap_block', '2u2'),
    ])
    MGL_DTYPE = dtype_to_moderngl(NP_DTYPE)

    def _build_buffer(self):
        self._capacity = 1024
        self._allocated = 0
        self._allocations = {}
        self._data = np.zeros((self._capacity,), dtype=self.NP_DTYPE)

    def _allocate(self, pos: Tuple[int, int]) -> int:
        if self._allocated >= self._capacity:
            raise NotImplementedError("resize is not implemented")

        idx = self._allocations[pos] = self._allocated
        self._allocated += 1
        return idx

    def _set_dirty(self):
        self.layer._dirty.add(self)

    @property
    def bounds(self):
        """todo"""
        raise NotImplementedError()

    def delete(self):
        """Delete this primitive."""
        self.layer._dirty.discard(self)
        self.layer.objects.discard(self)
        self.layer = None
