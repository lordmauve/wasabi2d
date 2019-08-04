import sys
import pygame
import moderngl
import rectpack
import numpy as np
from pyrr import Matrix44, Vector3, vector3


pygame.init()
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
screen = pygame.display.set_mode(
    (1600, 1200),
    flags=pygame.OPENGL | pygame.DOUBLEBUF,
    depth=24
)
ctx = moderngl.create_context()


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
                    r, t,
                    r, b,
                    l, b,
                    l, t,
                ], dtype='f4')
            else:
                texcoords = np.array([
                    l, t,
                    r, t,
                    r, b,
                    l, b
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



atlas = Atlas(ctx, ['ship.png'])



prog = ctx.program(
    vertex_shader='''
        #version 330

        uniform mat4 proj;

        in vec3 in_vert;
        in vec2 in_uv;
        out vec2 uv;

        void main() {
            gl_Position = proj * vec4(in_vert.xy, 0.0, 1.0);
            uv = in_uv;
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


indexes = np.array([0, 1, 2, 0, 2, 3], dtype='i4')
tex, uvs, vs = atlas['ship.png']
vbo = ctx.buffer(vs, dynamic=True)
uvbo = ctx.buffer(uvs.tobytes())
ibuf = ctx.buffer(indexes)
vao = ctx.vertex_array(
    prog,
    [
        (vbo, '3f', 'in_vert'),
        (uvbo, '2f', 'in_uv'),
    ],
    ibuf
)


def render(t, dt):
    ctx.clear(1.0, 1.0, 1.0)
    tex.use(0)
    vao.render()


clock = pygame.time.Clock()

t = 0

xlate = np.identity(3, dtype='f4')
rot = ident_rot = np.identity(3, dtype='f4')

proj = Matrix44.orthogonal_projection(
    left=0, right=800, top=600, bottom=0, near=-1000, far=1000,
).astype('f4')
prog['proj'].write(proj.tobytes())
prog['tex'].value = 0
ctx.enable(moderngl.BLEND)
ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

ship_pos = Vector3()
ship_v = Vector3()

Z = vector3.create_unit_length_z()

while True:
    dt = clock.tick(60) / 1000.0
    t += dt
    for ev in pygame.event.get():
        #print(ev)
        if ev.type == pygame.QUIT:
            sys.exit(0)

    keys = pygame.key.get_pressed()

    ship_v *= 0.5 ** dt

    accel = 100 * dt
    if keys[pygame.K_RIGHT]:
        ship_v[0] += accel
    elif keys[pygame.K_LEFT]:
        ship_v[0] -= accel
    if keys[pygame.K_UP]:
        ship_v[1] -= accel
    elif keys[pygame.K_DOWN]:
        ship_v[1] += accel

    ship_pos += ship_v * dt
    if vector3.length(ship_v):
        rx = vector3.normalize(ship_v)
        ry = vector3.cross(rx, Z)
        rot[0] = rx
        rot[1] = ry

    xlate[2][:2] = ship_pos[:2]
    vbo.write(vs @ (rot @ xlate))
    render(t, dt)
    pygame.display.flip()
