"""Pack sprites into texture atlases."""
from typing import Tuple, Optional
from dataclasses import dataclass

import moderngl
import numpy as np
import pygame
from pygame import Rect

from .loaders import images
from .allocators.textures import Packer, NoFit


class TexSurface:
    """A GPU texture.

    This class allows copying pygame Surfaces into regions of a texture on the
    GPU.
    """
    tex: moderngl.Texture
    _dirty: bool

    def __init__(self, tex: moderngl.Texture):
        self.tex = tex
        self._dirty = False

    @classmethod
    def new(cls, ctx: moderngl.Context, size: Tuple[int, int]) -> 'TexSurface':
        """Create a new TexSurface in the given moderngl context."""
        tex = ctx.texture(size, 4)
        return cls(tex)

    def write(self, img: pygame.Surface, rect: pygame.Rect):
        """Write the contents of img at the given coordinates."""
        imgdata = pygame.image.tostring(img, "RGBA", 1)
        self.tex.write(imgdata, (rect.x, rect.y, rect.width, rect.height))
        self._dirty = True

    def update(self):
        """Sync texture data to the GPU."""
        self.tex.build_mipmaps(max_level=2)
        self._dirty = False

    def save(self, fname: str):
        """Save the contents of the texture to a file.

        This is intended for debugging.
        """
        w, h = self.tex.width, self.tex.height
        data = self.tex.read(components=4)
        assert len(data) == (w * h * 5), \
            f"Received {len(data)}, expected {w * h * 4}"
        img = pygame.image.fromstring(data, (w, h), 'RGBA')
        img = pygame.transform.flip(img, False, True)
        pygame.image.save(img, fname)

    def use(self, texunit: int):
        """Shortcut to bind the texture to a texture unit."""
        self.tex.use(texunit)


@dataclass
class TextureRegion:
    """An allocated region of a texture."""
    tex: moderngl.Texture
    width: int
    height: int
    texcoords: np.ndarray

    def __post_init__(self):
        w = self.width
        h = self.height
        self.verts = np.array([
            (0, 0, 1),
            (w, 0, 1),
            (w, h, 1),
            (0, h, 1),
        ], dtype='f4')

    def get_verts(
        self,
        anchor_x: Optional[int] = None,
        anchor_y: Optional[int] = None
    ) -> np.ndarray:
        """Get an array or transformed vertices."""
        offset = (
            anchor_x if anchor_x is not None else self.width / 2,
            anchor_y if anchor_y is not None else self.height / 2,
            0.0
        )
        vs = self.verts.copy()
        vs -= offset
        return vs


class Atlas:
    """Texture atlas generator.

    Newly requested textures are positioned using a packer and then written
    to a texture using a TexSurface.

    """

    def __init__(self, ctx, *, texsize=512, padding=2):
        self.ctx = ctx
        self.padding = padding
        self.texsize = texsize

        self.packer = Packer.new_shelves(size=texsize)

        self.surfs_texs = []
        self.tex_for_name = {}

    def _load(self, name):
        """Load the image for the given name."""
        return images.load(name)

    def mksurftex(self, size: Tuple[int, int]) -> TexSurface:
        """Make a new surface and corresponding texture of the given size."""
        texsurf = TexSurface.new(self.ctx, size)
        self.surfs_texs.append(texsurf)
        return texsurf

    def npot_tex(self, sprite_name, img):
        """Get a non-power-of-two texture for this image."""
        w, h = size = img.get_size()
        tex = self.ctx.texture(size, 4)
        tex.write(pygame.image.tostring(img, "RGBA", 1))
        tex.build_mipmaps(max_level=2)
        texcoords = np.array([
            (0, h),
            (w, h),
            (w, 0),
            (0, 0),
        ], dtype=np.uint16)

        texregion = TextureRegion(tex, w, h, texcoords)
        res = self.tex_for_name[sprite_name] = texregion
        return res

    def get(self, sprite_name):
        if sprite_name in self.tex_for_name:
            return self.tex_for_name[sprite_name]

        img = self._load(sprite_name)

        pad = self.padding * 2

        orig = img.get_rect()
        r = Rect(orig)
        r.w += pad
        r.h += pad
        try:
            bin, packed = self.packer.add(r)
        except NoFit:
            # Does not fit in packer bounds
            return self.npot_tex(sprite_name, img)

        p = Rect(packed)
        p.left += self.padding
        p.top += self.padding
        p.w -= pad
        p.h -= pad

        try:
            texsurf = self.surfs_texs[bin]
        except IndexError:
            size = (self.texsize, self.texsize)
            texsurf = self.mksurftex(size)

        rotated = False
        if orig.w != p.w:
            img = pygame.transform.rotate(img, -90)
            rotated = True

        x, y = p.topleft
        w, h = p.size

        texsurf.write(img, p)

        l = p.left
        b = p.top
        r = p.right
        t = p.bottom

        if rotated:
            texcoords = np.array([
                (r, t),
                (r, b),
                (l, b),
                (l, t),
            ], dtype=np.uint16)
            w, h = h, w
        else:
            texcoords = np.array([
                (l, t),
                (r, t),
                (r, b),
                (l, b),
            ], dtype=np.uint16)

        texregion = TextureRegion(texsurf, w, h, texcoords)
        res = self.tex_for_name[sprite_name] = texregion
        return res

    def _update(self):
        """Copy updated surfaces to the GL texture objects."""
        for surftex in self.surfs_texs:
            if surftex._dirty:
                surftex.update()

    def dump(self):
        """Save screenshots of all the textures."""
        for i, surftex in enumerate(self.surfs_texs):
            surftex.save(f'atlas{i}.png')
