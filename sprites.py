import sys
import math
import pygame
import moderngl
import rectpack
import numpy as np
from typing import Any, Optional
from pyrr import Matrix44, Vector3, vector3, matrix33
from dataclasses import dataclass, field


pygame.init()
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
pygame.display.gl_set_attribute(
    pygame.GL_CONTEXT_PROFILE_MASK,
    pygame.GL_CONTEXT_PROFILE_CORE
)
screen = pygame.display.set_mode(
    (1600, 1200),
    flags=pygame.OPENGL | pygame.DOUBLEBUF,
    depth=24
)
ctx = moderngl.create_context()


Z = vector3.create_unit_length_z()


class Atlas:
    def __init__(self, ctx, sprites, *, padding=2):
        self.padding = padding

        self.next_id = 0
        self.packer = rectpack.newPacker()
        self.packer.add_bin(512, 512, count=10)
        self.sprites = {}

        self.tex_for_name = {}

        for sprite in sprites:
            self._add(sprite)

        self.packer.pack()

        n_texs = len(self.packer)
        self.surfs = [
            pygame.Surface((512, 512), pygame.SRCALPHA, depth=32)
            for _ in range(n_texs)
        ]

        for bin, x, y, w, h, (img, spritename) in self.packer.rect_list():
            orig_w, orig_h = img.get_size()
            rotated = False
            if orig_w != w:
                img = pygame.transform.rotate(img, -90)
                rotated = True

            dest = self.surfs[bin]
            dest.blit(img, (x + self.padding, y + self.padding))

            l = (x + self.padding) / 512
            t = 1.0 - (y + self.padding) / 512
            r = (x + w - self.padding) / 512
            b = 1.0 - (y + h - self.padding) / 512

            if rotated:
                texcoords = np.array([
                    (r, t),
                    (r, b),
                    (l, b),
                    (l, t),
                ], dtype='f4')
            else:
                texcoords = np.array([
                    (l, t),
                    (r, t),
                    (r, b),
                    (l, b),
                ], dtype='f4')
            verts = np.array([
                (0, orig_h, 1),
                (orig_w, orig_h, 1),
                (orig_w, 0, 1),
                (0, 0, 1),
            ], dtype='f4')
            verts -= (orig_w / 2, orig_h / 2, 0)
            self.tex_for_name[spritename] = (bin, texcoords, verts)

        # Save textures, for debugging
        for i, s in enumerate(self.surfs):
            pygame.image.save(s, f'atlas{i}.png')

        self.texs = []
        for t in self.surfs:
            tex = ctx.texture(
                t.get_size(),
                4,
                data=pygame.image.tostring(t, "RGBA", 1),
            )
            tex.build_mipmaps(max_level=2)
            self.texs.append(tex)

        for name, (bin, uvs, vs) in self.tex_for_name.items():
            self.tex_for_name[name] = self.texs[bin], uvs, verts

    def __getitem__(self, k):
        return self.tex_for_name[k]

    def _add(self, spritename):
        id = self.next_id
        self.next_id += 1

        img = pygame.image.load(spritename)
        self.sprites[spritename] = (img, id)

        pad = self.padding * 2
        w, h = img.get_size()
        self.packer.add_rect(w + pad, h + pad, (img, spritename))


atlas = Atlas(ctx, ['ship.png', 'tiny_bullet.png'])


tex_quads_prog = ctx.program(
    vertex_shader='''
        #version 330

        uniform mat4 proj;

        in vec3 in_vert;
        in vec4 in_color;
        in vec2 in_uv;
        out vec2 uv;
        out vec4 color;

        void main() {
            gl_Position = proj * vec4(in_vert.xy, 0.0, 1.0);
            uv = in_uv;
            color = in_color;
        }
    ''',
    fragment_shader='''
        #version 330

        out vec4 f_color;
        in vec2 uv;
        in vec4 color;
        uniform sampler2D tex;

        void main() {
            f_color = color * texture(tex, uv);
        }
    ''',
)


class SpriteArray:
    """Vertex array object to hold textured quads."""
    QUAD = np.array([0, 1, 2, 0, 2, 3], dtype='i4')

    def __init__(self, ctx, tex, sprites):
        self.tex = tex
        self.sprites = list(sprites)
        self._allocate()

    def _allocate(self):
        self.allocated = len(self.sprites)

        # Allocate extra slots in the arrays for faster additions
        extra = max(32 - self.allocated, self.allocated // 2)

        for i, s in enumerate(self.sprites):
            s.array = self
            s.offset = i
            if s.verts is None:
                s._update()

        self.indexes = np.vstack([
            self.QUAD + 4 * i
            for i in range(self.allocated + extra)
        ])
        self.uvs = np.vstack(
            [s.uvs for s in self.sprites]
            + [np.zeros((4 * extra, 2), dtype='f4')]
        )
        self.verts = np.vstack(
            [s.verts for s in self.sprites]
            + [np.zeros((4 * extra, 7), dtype='f4')]
        )

        self.vbo = ctx.buffer(self.verts, dynamic=True)
        self.uvbo = ctx.buffer(self.uvs)
        self.ibuf = ctx.buffer(self.indexes)
        self.vao = ctx.vertex_array(
            tex_quads_prog,
            [
                (self.vbo, '3f 4f', 'in_vert', 'in_color'),
                (self.uvbo, '2f', 'in_uv'),
            ],
            self.ibuf
        )

    def add(self, s):
        """Add a sprite to the array.

        If there's unallocated space in the VBO we append the sprite.

        Otherwise we allocate new VBOs.
        """
        s.array = self
        if not s.verts:
            s._update()
        size = len(self.verts) // 4
        if self.allocated < size:
            i = self.allocated
            self.allocated += 1
            self.verts[i * 4:i * 4 + 4] = s.verts
            self.uvs[i * 4:i * 4 + 4] = s.uvs
            self.sprites.append(s)
            s.offset = i

            #TODO: We can send less data with write_chunks()
            self.vbo.write(self.verts)
            self.uvbo.write(self.uvs)
        else:
            self.sprites.append(s)
            self._allocate()

    def delete(self, s):
        """Remove a sprite from the array.

        To do this without resizing the buffer we move a sprite from the
        end of the array into the gap. This means that draw order changes.

        """
        assert s.array is self
        i = s.offset
        j = self.allocated - 1
        self.allocated -= 1
        if i == j:
            self.sprites.pop()
        else:
            moved = self.sprites[i] = self.sprites[j]
            self.sprites.pop()
            moved.offset = i
            self.verts[i * 4:i * 4 + 4] = self.verts[j * 4:j * 4 + 4]
            self.uvs[i * 4:i * 4 + 4] = self.uvs[j * 4:j * 4 + 4]
            # TODO: write only once per frame no matter how many adds/deletes
            self.vbo.write(self.verts)
            self.uvbo.write(self.uvs)
        s.array = None

    def render(self):
        tex_quads_prog['tex'].value = 0
        self.tex.use(0)
        dirty = False
        for i, s in enumerate(self.sprites):
            if s.verts is None:
                s._update()
                self.verts[i * 4:i * 4 + 4] = s.verts
                dirty = True
        assert self.verts.dtype == 'f4', \
            f"Dtype of verts is {self.verts.dtype}"
        if dirty:
            self.vbo.write(self.verts)
        self.vao.render(vertices=self.allocated * 6)


class Layer:
    def __init__(self, ctx, group):
        self.ctx = ctx
        self.group = group
        self.arrays = {}
        self.objects = []

    def render(self):
        for a in self.arrays.values():
            a.render()

    def add_sprite(self, image, pos=(0, 0), angle=0):
        tex, uvs, vs = atlas[image]
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
            array = SpriteArray(ctx, tex, [spr])
            self.arrays[k] = array
        else:
            array.add(spr)
        return spr


@dataclass
class Sprite:
    image: str
    _angle: float

    uvs: np.ndarray
    orig_verts: np.ndarray
    verts: Optional[np.ndarray] = None

    _scale: np.ndarray = field(
        default_factory=lambda: np.identity(3, dtype='f4')
    )
    _rot: np.ndarray = field(
        default_factory=lambda: np.identity(3, dtype='f4')
    )
    _xlate: np.ndarray = field(
        default_factory=lambda: np.identity(3, dtype='f4')
    )
    _color: np.ndarray = field(
        default_factory=lambda: np.ones((4, 4), dtype='f4')
    )

    array: Any = None
    offset: int = 0

    def delete(self):
        self.array.delete(self)

    @property
    def color(self):
        return tuple(self.color[0])

    @color.setter
    def color(self, v):
        self._color[:] = v
        self.verts = None

    @property
    def pos(self):
        return self._xlate[2][:2]

    @pos.setter
    def pos(self, v):
        assert len(v) == 2
        self._xlate[2][:2] = v
        self.verts = None

    @property
    def scale(self):
        p = self._scale[0, 0] * self._scale[1, 1]
        return math.copysign(math.sqrt(abs(p)), p)

    @scale.setter
    def scale(self, v):
        self._scale[0, 0] = self._scale[1, 1] = v
        self.verts = None

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, theta):
        assert isinstance(theta, (int, float))
        self._rot = matrix33.create_from_axis_rotation(Z, theta, dtype='f4')
        self._angle = theta
        self.verts = None

    def _update(self):
        xform = self._scale @ self._rot @ self._xlate

        self.verts = np.hstack([
            self.orig_verts @ xform,
            self._color
        ])


class LayerGroup(dict):
    def __new__(cls, ctx):
        return dict.__new__(cls)

    def __init__(self, ctx):
        self.ctx = ctx

    def __missing__(self, k):
        if not isinstance(k, (float, int)):
            raise TypeError("Layer indices must be numbers")
        layer = self[k] = Layer(self.ctx, self)
        return layer

    def render(self):
        for k in sorted(self):
            self[k].render()


layers = LayerGroup(ctx)
ship = layers[0].add_sprite('ship.png')


def render(t, dt):
    ctx.clear(1.0, 1.0, 1.0)
    layers.render()


clock = pygame.time.Clock()

t = 0


proj = Matrix44.orthogonal_projection(
    left=0, right=800, top=600, bottom=0, near=-1000, far=1000,
).astype('f4')
tex_quads_prog['proj'].write(proj.tobytes())
ctx.enable(moderngl.BLEND)
ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

ship_pos = Vector3()
ship_v = Vector3()


bullets = []

while True:
    dt = clock.tick(60) / 1000.0
    t += dt

    fire = False
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            sys.exit(0)
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_SPACE:
                fire = True

    if fire:
        bullet = layers[0].add_sprite('tiny_bullet.png', pos=ship.pos)
        bullet.color = (1, 0, 0, 1)
        bullet.vel = vector3.normalize(ship_v) * 100
        bullet.power = 1.0
        bullets.append(bullet)

    keys = pygame.key.get_pressed()

    ship_v *= 0.3 ** dt

    accel = 300 * dt
    if keys[pygame.K_RIGHT]:
        ship_v[0] += accel
    elif keys[pygame.K_LEFT]:
        ship_v[0] -= accel
    if keys[pygame.K_UP]:
        ship_v[1] -= accel
    elif keys[pygame.K_DOWN]:
        ship_v[1] += accel

    ship_vx, ship_vy, _ = ship_v
    ship_pos += ship_v * dt

    ship.pos = ship_pos[:2]
    if not (-1e-6 < ship_vx < 1e-6 and -1e-6 < ship_vy < -1e-6):
        ship.angle = math.atan2(ship_vy, ship_vx)

    for b in bullets.copy():
        b.power *= 0.5 ** dt
        b.angle += 3 * dt
        b.scale = b.power
        b.color = (1, 0, 0, b.power ** 0.5)
        if b.scale < 0.01:
            b.delete()
            bullets.remove(b)

    render(t, dt)
    pygame.display.flip()
