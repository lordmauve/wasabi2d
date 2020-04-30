from typing import Tuple, Optional, Any
import importlib
import weakref

import moderngl
import pygame.image

from .clock import default_clock
from .atlas import Atlas
from .primitives.sprites import SpriteArray, Sprite
from .primitives.circles import Circle, line_vao, shape_vao
from .primitives.polygons import Polygon, Rect, PolyLine
from .primitives.text import Label, FontAtlas, text_vao
from .primitives.particles import ParticleGroup, ParticleVAO, PARTICLE_PROGRAM
from .loaders import images
from .shaders import ShaderManager


class FontManager:
    def __init__(self, ctx):
        self.ctx = ctx
        self.font_atlases = {}

    def get(self, font_name):
        try:
            return self.font_atlases[font_name]
        except KeyError:
            fa = self.font_atlases[font_name] = FontAtlas(self.ctx, font_name)
            return fa

    def update(self):
        """Send any dirty textures to the GL."""
        for f in self.font_atlases.values():
            f._update()


class Layer:
    def __init__(self, ctx, group):
        self.ctx = ctx
        self.group = group
        self.arrays = weakref.WeakValueDictionary()
        self.visible = True
        self.objects = set()
        self._dirty = set()
        self.effect = None

    def clear(self):
        """Remove everything from the layer."""
        # We need to release GL buffers we hold; everything else can be
        # destroyed by the GC.
        for a in self.arrays.values():
            a.release()
        self.arrays.clear()
        self.objects.clear()
        self._dirty.clear()

    def _draw(self):
        """Render the layer."""
        if not self.visible:
            return

        for o in self._dirty:
            o._update()
        self._dirty.clear()

        if self.effect:
            self.effect.draw(self._draw_inner)
        else:
            self._draw_inner()

    def _draw_inner(self):
        for a in self.arrays.values():
            a.render(self.group.camera)

    def set_effect(self, name: str, **kwargs) -> Any:
        """Set the post processing effect to use for the layer.

        Return the effect object, which can be used to change parameters for
        the effect.

        """
        mod = importlib.import_module(f'wasabi2d.effects.{name}')
        cls = getattr(mod, name.title())
        self.effect = cls(self.ctx, **kwargs)
        self.effect._set_camera(self.group.camera)
        return self.effect

    def clear_effect(self):
        self.effect = None

    def add_sprite(
        self,
        image,
        *,
        pos=(0, 0),
        angle=0,
        anchor_x='center',
        anchor_y='center',
        color=(1, 1, 1, 1),
        scale=1.0
    ):
        spr = Sprite(
            layer=self,
            image=image,
            anchor_x=anchor_x,
            anchor_y=anchor_y,
        )
        spr.pos = pos
        spr.angle = angle
        spr.color = color
        spr.scale = scale
        self.objects.add(spr)
        return spr

    def _migrate_sprite(self, spr, tex):
        """Move sprite spr into the correct vertex array."""
        k = ('sprite', id(tex))
        array = self.arrays.get(k)
        if not array:
            prog = self.group.shadermgr.get(**SpriteArray.PROGRAM)
            array = SpriteArray(self.ctx, prog, tex, [spr])
            self.arrays[k] = array
        else:
            array.add(spr)

    def _delete_sprite_array(self, array):
        tex = array.tex
        k = ('sprite', id(tex))
        if k in self.arrays:
            del self.arrays[k]

    def _get_or_create_vao(self, k, constructor):
        """Get a VAO identified by key k, or construct it using constructor."""
        vao = self.arrays.get(k)
        if not vao:
            vao = self.arrays[k] = constructor(self.ctx, self.group.shadermgr)
        return vao

    def _lines_vao(self):
        """Get a VAO for objects made of line strips."""
        return self._get_or_create_vao('lines', line_vao)

    def _fill_vao(self):
        """Get a VAO for objects made of colored triangles."""
        return self._get_or_create_vao('shapes', shape_vao)

    def _load_texture(self, name):
        """Load a texture."""
        img = images.load(name)
        data = pygame.image.tostring(img, "RGBA", 1)
        tex = self.ctx.texture(img.get_size(), 4, data=data)
        tex.build_mipmaps(max_level=2)
        return tex

    def _text_vao(self, font):
        """Get a VAO for objects made of font glyphs."""
        return self._get_or_create_vao(('text', font), text_vao)

    def add_circle(self,
                   *,
                   radius: float,
                   pos: Tuple[float, float] = (0, 0),
                   color: Tuple[float, float, float, float] = (1, 1, 1, 1),
                   fill: bool = True,
                   stroke_width: float = 1.0,
                   ) -> Circle:
        c = Circle(
            layer=self,
            radius=radius,
            pos=pos,
            color=color,
            stroke_width=stroke_width,
        )
        if fill:
            c._migrate_fill(self._fill_vao())
        else:
            c._migrate_stroke(self._lines_vao())
        self.objects.add(c)
        return c

    def add_star(
            self,
            *,
            points: int,
            inner_radius: float = 1.0,
            outer_radius: float = None,
            pos: Tuple[float, float] = (0, 0),
            fill: bool = True,
            color: Tuple[float, float, float, float] = (1, 1, 1, 1),
            stroke_width: float = 1.0,
    ) -> Circle:
        assert points >= 3, "Stars must have at least 3 points."

        if outer_radius is None:
            outer_radius = inner_radius * 2

        c = Circle(
            layer=self,
            segments=2 * points + 1,
            radius=1.0,
            pos=pos,
            color=color,
            stroke_width=stroke_width,
        )
        if fill:
            c._migrate_fill(self._fill_vao())
        else:
            c._migrate_stroke(self._lines_vao())
        self.objects.add(c)
        c.orig_verts[::2, :2] *= outer_radius
        c.orig_verts[1::2, :2] *= inner_radius
        return c

    def add_polygon(self,
                    vertices,
                    *,
                    pos: Tuple[float, float] = (0, 0),
                    color: Tuple[float, float, float, float] = (1, 1, 1, 1),
                    fill: bool = True,
                    stroke_width: float = 1.0,
                    ) -> Polygon:
        c = Polygon(
            layer=self,
            vertices=vertices,
            pos=pos,
            color=color,
            stroke_width=stroke_width,
        )
        self.objects.add(c)
        if fill:
            c._migrate_fill(self._fill_vao())
        else:
            c._migrate_stroke(self._lines_vao())
        return c

    def add_line(self,
                 vertices,
                 *,
                 pos: Tuple[float, float] = (0, 0),
                 color: Tuple[float, float, float, float] = (1, 1, 1, 1),
                 stroke_width: float = 1.0,
                 ) -> PolyLine:
        """Add a line strip.

        To create a single line segment of two points, pass two vertices!

        """
        c = PolyLine(
            layer=self,
            vertices=vertices,
            pos=pos,
            color=color,
            stroke_width=stroke_width,
        )
        self.objects.add(c)
        c._migrate_stroke(self._lines_vao())
        return c

    def add_rect(
            self,
            width: float,
            height: float,
            *,
            pos: Tuple[float, float] = (0, 0),
            color: Tuple[float, float, float, float] = (1, 1, 1, 1),
            fill: bool = True,
            stroke_width: float = 1) -> Rect:

        c = Rect(
            layer=self,
            width=width,
            height=height,
            pos=pos,
            color=color,
            stroke_width=stroke_width,
        )
        self.objects.add(c)
        if fill:
            c._migrate_fill(self._fill_vao())
        else:
            c._migrate_stroke(self._lines_vao())
        return c

    def add_label(self,
                  text: str,
                  *,
                  font: Optional[str] = None,
                  align: str = 'left',
                  fontsize: int = 20,
                  pos: Tuple[float, float] = (0, 0),
                  color: Tuple[float, float, float, float] = (1, 1, 1, 1),
                  ) -> Rect:

        fa = self.group.fontmgr.get(font)
        c = Label(
            text,
            fa,
            self,
            align=align,
            fontsize=fontsize,
            pos=pos,
            color=color
        )
        self.objects.add(c)
        return c

    def add_particle_group(
        self,
        texture=None,
        clock=default_clock,
        **kwargs
    ) -> ParticleGroup:
        """Create a group of particles.

        We do not actually emit any particles at this time.
        """
        c = ParticleGroup(
            layer=self,
            clock=default_clock,
            **kwargs
        )

        vao = self.arrays[c] = ParticleVAO(
            c,
            mode=moderngl.POINTS,
            ctx=self.ctx,
            prog=self.group.shadermgr.get(**PARTICLE_PROGRAM),
        )
        if texture is None:
            tex = self.ctx.texture((1, 1), 4, data=b'\xff' * 4)
        else:
            tex = self._load_texture(texture)
            tex.repeat_x = tex.repeat_y = False
        vao.tex = tex
        vao.color_tex = c.color_tex

        self.objects.add(c)
        c._migrate(vao)
        return c


class LayerGroup(dict):
    def __new__(cls, ctx, camera):
        return dict.__new__(cls)

    def __init__(self, ctx, camera):
        self.ctx = ctx
        self.camera = camera
        self.shadermgr = ShaderManager(self.ctx)
        self.fontmgr = FontManager(self.ctx)
        self.atlas = Atlas(ctx)

    def __missing__(self, k):
        if not isinstance(k, (float, int)):
            raise TypeError("Layer indices must be numbers")
        layer = self[k] = Layer(self.ctx, self)
        return layer

    def _update(self, proj):
        # TODO: dirtymgr to manage these
        self.atlas._update()
        self.fontmgr.update()

        # TODO: let the chain handle this
        self.shadermgr.set_proj(proj)

    def clear(self):
        """Clear the layer group.

        We override this to explicitly release resources.
        """
        for v in self.values():
            v.clear()
        super().clear()
