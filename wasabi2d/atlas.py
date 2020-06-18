"""Pack sprites into texture atlases."""
from typing import Tuple, Optional, List, Union
from dataclasses import dataclass

import moderngl
import numpy as np
import pygame
from pygame import Rect

from .loaders import images
from .allocators.textures import Packer, NoFit
from .primitives.sprites import QUAD
from .shaders import shadermgr, blend_func, bind_framebuffer


BLIT_PROGRAM = dict(
    vertex_shader='''
        #version 330

        in ivec2 in_uv;
        uniform ivec2 newsize;
        out vec2 uv;
        uniform sampler2D tex;

        const vec2 BL = vec2(-1, -1);

        void main() {
            vec2 v = vec2(in_uv) / newsize;
            gl_Position = vec4(v * 2 + BL, 0.0, 1.0);
            uv = vec2(in_uv) / textureSize(tex, 0);
        }
    ''',
    fragment_shader='''
        #version 330

        out vec4 f_color;
        in vec2 uv;
        uniform sampler2D tex;

        void main() {
            f_color = texture(tex, uv);
        }
    ''',
)


class TexSurface:
    """A GPU texture.

    This class allows copying pygame Surfaces into regions of a texture on the
    GPU.
    """
    ctx: moderngl.Context
    tex: moderngl.Texture
    _dirty: bool

    def __init__(self, ctx: moderngl.Context, tex: moderngl.Texture):
        self.ctx = ctx
        self.tex = tex
        self._dirty = False

    @property
    def width(self):
        """Get the current width of the texture."""
        return self.tex.width

    @property
    def height(self):
        """Get the current height of the texture."""
        return self.tex.height

    @classmethod
    def new(cls, ctx: moderngl.Context, size: Tuple[int, int]) -> 'TexSurface':
        """Create a new TexSurface in the given moderngl context."""
        tex = ctx.texture(size, 4)
        return cls(ctx, tex)

    def resize(self, newsize: Tuple[int, int]):
        """Resize the texture and copy the existing data into it."""
        newtex = self.ctx.texture(newsize, 4)
        in_region = TextureRegion.for_tex(self.tex)
        vdata = in_region.texcoords

        vs = self.ctx.buffer(vdata)
        ibuf = self.ctx.buffer(QUAD)
        prog = shadermgr(self.ctx).get(**BLIT_PROGRAM)
        self.tex.use(0)
        self.tex.filter = moderngl.NEAREST, moderngl.NEAREST
        prog['tex'].value = 0
        prog['newsize'].value = newsize
        vao = self.ctx.vertex_array(
            prog,
            [
                (vs, '2u2', 'in_uv'),
            ],
            ibuf
        )
        fb = self.ctx.framebuffer(color_attachments=[newtex])
        with bind_framebuffer(self.ctx, fb), \
                blend_func(self.ctx, moderngl.ONE, moderngl.ZERO):
            vao.render(vertices=6)
        self._dirty = True
        self.tex.release()
        self.tex = newtex

    def write(self, img: pygame.Surface, rect: pygame.Rect):
        """Write the contents of img at the given coordinates."""
        imgdata = pygame.image.tostring(img, "RGBA", 1)
        self.tex.write(imgdata, (rect.x, rect.y, rect.width, rect.height))
        self._dirty = True

    def update(self):
        """Sync texture data to the GPU."""
        self.tex.build_mipmaps(max_level=2)
        self.tex.filter = self.ctx.extra['texture_filter']
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

    def __del__(self):
        self.tex.release()


@dataclass
class TextureRegion:
    """An allocated region of a texture."""
    tex: TexSurface
    width: int
    height: int
    texcoords: np.ndarray
    rot: int = 0

    def __post_init__(self):
        if not isinstance(self.rot, int):
            raise TypeError(f"rot must be int, not {self.rot!r}")
        if self.texcoords.dtype != np.uint16:
            raise TypeError(
                f"Invalid dtype {self.texcoords.dtype} for tex coords"
            )
        w = self.width
        h = self.height
        self.verts = np.array([
            (0, 0, 1),
            (w, 0, 1),
            (w, h, 1),
            (0, h, 1),
        ], dtype='f4')

    @classmethod
    def for_tex(cls, tex):
        """Create a TextureRegion corresponding to the whole of tex."""
        return cls.for_rect(tex, Rect(0, 0, tex.width, tex.height))

    def absregion(self) -> Rect:
        """Get the region of the original texture."""
        (l, t), (r, b) = self.texcoords[[0, 2]].astype(int)
        w = abs(l - r)
        h = abs(b - t)
        l = min(l, r)
        t = min(b, t)
        return Rect(l, t, w, h)

    @classmethod
    def for_rect(cls, tex, rect: Rect):
        """Create a TextureRegion for the given texture and rect."""
        if isinstance(tex, TextureRegion):
            assert rect.width and rect.height, "Invalid rect dimensions"
            myrect = Rect(0, 0, tex.width, tex.height)
            assert myrect.contains(rect), "Subrect is not in bounds."

            coords = tex.texcoords.astype(np.int32)
            lb = coords[3]
            r = np.sign(coords[2] - lb)
            u = np.sign(coords[0] - lb)
            lb += r * rect.left + u * rect.top
            across = r * rect.width
            up = u * rect.height
            texcoords = np.array([
                lb + up,
                lb + up + across,
                lb + across,
                lb,
            ], dtype=np.uint16)
            rot = tex.rot
            tex = tex.tex
        else:
            rot = 0

            l = rect.left
            b = rect.top
            r = rect.right
            t = rect.bottom
            texcoords = np.array([
                (l, t),
                (r, t),
                (r, b),
                (l, b),
            ], dtype=np.uint16)
        return cls(
            tex,
            rect.width,
            rect.height,
            texcoords,
            rot
        )

    def write(self, img: pygame.Surface):
        """Write the given surface into this region."""
        if self.rot:
            img = pygame.transform.rotate(img, self.rot)
        sz = img.get_size()
        bounds = self.absregion()
        assert sz == bounds.size, f"{sz!r} != {bounds.size!r}"
        self.tex.write(img, bounds)

    def rotated(self):
        """Get the view of this texture region rotated by 90 degrees."""
        newcoords = self.texcoords[[1, 2, 3, 0]]
        return TextureRegion(
            self.tex,
            self.height,
            self.width,
            newcoords,
            self.rot - 90,
        )

    ANCHOR_X_NAMES = {
        'left': 0,
        'center': 0.5,
        'right': 1,
    }
    ANCHOR_Y_NAMES = {
        'top': 0,
        'center': 0.5,
        'bottom': 1,
    }

    def get_verts(
        self,
        anchor_x: Union[float, str] = 'center',
        anchor_y: Union[float, str] = 'center',
    ) -> np.ndarray:
        """Get an array or transformed vertices."""
        if isinstance(anchor_x, str):
            anchor_x = self.width * self.ANCHOR_X_NAMES[anchor_x]
        if isinstance(anchor_y, str):
            anchor_y = self.height * self.ANCHOR_Y_NAMES[anchor_y]
        offset = (float(anchor_x), float(anchor_y), 0.0)
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

        self.texsurf: Optional[TexSurface] = None
        self.surfs_texs: List[TextureRegion] = []
        self.tex_for_name = {}

    def _load(self, name):
        """Load the image for the given name."""
        return images.load(name)

    def mksurftex(self) -> TextureRegion:
        """Make a new surface and corresponding texture of the given size."""
        if not self.texsurf:
            self.texsurf = TexSurface.new(self.ctx, (self.texsize,) * 2)
            region = TextureRegion.for_tex(self.texsurf)
        else:
            count = len(self.surfs_texs)
            self.texsurf.resize((
                (count + 1) * self.texsize,
                self.texsize
            ))
            region = TextureRegion.for_rect(
                self.texsurf,
                Rect(count * self.texsize, 0, self.texsize, self.texsize)
            )

        self.surfs_texs.append(region)
        return region

    def npot_tex(self, sprite_name, img):
        """Get a non-power-of-two texture for this image."""
        w, h = size = img.get_size()
        tex = self.ctx.texture(size, 4)
        tex.write(pygame.image.tostring(img, "RGBA", 1))
        tex.build_mipmaps()
        tex.filter = self.ctx.extra['texture_filter']
        tex.repeat_x = tex.repeat_y = False
        texcoords = np.array([
            (0, h),
            (w, h),
            (w, 0),
            (0, 0),
        ], dtype=np.uint16)

        texregion = TextureRegion(TexSurface(self.ctx, tex), w, h, texcoords)
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
            reg = self.surfs_texs[bin]
        except IndexError:
            reg = self.mksurftex()

        texregion = TextureRegion.for_rect(reg, p)
        if orig.w != p.w:
            texregion = texregion.rotated()
        texregion.write(img)

        res = self.tex_for_name[sprite_name] = texregion
        return res

    def _update(self):
        """Copy updated surfaces to the GL texture objects."""
        if self.texsurf and self.texsurf._dirty:
            self.texsurf.update()

    def dump(self):
        tex = self.texsurf.tex
        data = tex.read()
        img = pygame.image.fromstring(data, (tex.width, tex.height), 'RGBA')
        img = pygame.transform.flip(img, False, True)
        pygame.image.save(img, 'atlas.png')
