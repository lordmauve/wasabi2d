from typing import Union, Tuple
import numpy as np
from pygame import Color

from .sprites import SpriteArray, Sprite
from .atlas import Atlas


def convert_color(c: Union[str, tuple]) -> Tuple[float, float, float, float]:
    """Convert a color to an RGBA tuple."""
    if isinstance(c, str):
        col = Color(c)
    else:
        col = Color(*c)

    return np.array(memoryview(col), dtype='u1').astype('f4')


class ShaderManager:
    def __init__(self, ctx):
        self.ctx = ctx
        self.programs = {}

    def get(self, vertex_shader, fragment_shader):
        """Get a compiled program."""
        k = vertex_shader, fragment_shader
        try:
            return self.programs[k]
        except KeyError:
            prog = self.programs[k] = self.ctx.program(
                vertex_shader=vertex_shader,
                fragment_shader=fragment_shader,
            )
            return prog

    def set_proj(self, proj):
        """Set the projection matrix."""
        for prog in self.programs.values():
            prog['proj'].write(proj.tobytes())


class Layer:
    def __init__(self, ctx, group):
        self.ctx = ctx
        self.group = group
        self.arrays = {}
        self.objects = []

    def render(self, t, dt):
        for a in self.arrays.values():
            a.render()

    def add_sprite(self, image, pos=(0, 0), angle=0):
        tex, uvs, vs = self.group.atlas[image]
        spr = Sprite(
            image=image,
            _angle=angle,
            uvs=np.copy(uvs),
            orig_verts=np.copy(vs),
        )
        spr.pos = pos
        spr.angle = angle
        spr.uvs = uvs
        k = ('sprite', tex.glo)
        array = self.arrays.get(k)
        if not array:
            prog = self.group.shadermgr.get(**SpriteArray.PROGRAM)
            array = SpriteArray(self.ctx, prog, tex, [spr])
            self.arrays[k] = array
        else:
            array.add(spr)
        return spr

    def add_circle(self, radius, pos=(0, 0), color=(1, 1, 1, 1)):
        color = convert_color()
        return Circle(
            radius=radius,
            pos=pos,
            color=color
        )


class LayerGroup(dict):
    def __new__(cls, ctx):
        return dict.__new__(cls)

    def __init__(self, ctx):
        self.ctx = ctx
        self.shadermgr = ShaderManager(self.ctx)
        self.atlas = Atlas(ctx, ['ship.png', 'tiny_bullet.png'])

    def __missing__(self, k):
        if not isinstance(k, (float, int)):
            raise TypeError("Layer indices must be numbers")
        layer = self[k] = Layer(self.ctx, self)
        return layer

    def render(self, proj, t, dt):
        self.shadermgr.set_proj(proj)
        for k in sorted(self):
            self[k].render(t, dt)
