import numpy as np

from .sprites import SpriteArray, Sprite
from .atlas import Atlas


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
        self.objects = set()
        self._dirty = set()

    def render(self, t, dt):
        for o in self._dirty:
            o._update()
        self._dirty.clear()
        for a in self.arrays.values():
            a.render()

    def add_sprite(self, image, pos=(0, 0), angle=0):
        tex, uvs, vs = self.group.atlas[image]
        spr = Sprite(
            layer=self,
            image=image,
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
        self.objects.add(spr)
        return spr

    def add_circle(self, radius, pos=(0, 0), color=(1, 1, 1, 1)):
        from .primitives.circles import Circle, line_vao
        c = Circle(
            layer=self,
            radius=radius,
            pos=pos,
            color=color
        )

        k = 'lines'
        vao = self.arrays.get(k)
        if not vao:
            vao = self.arrays[k] = line_vao(self.ctx, self.group.shadermgr)

        c._migrate(vao)
        self.objects.add(c)
        return c


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
