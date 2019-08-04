# Wasabi Engine 2

I wanted to explore using `moderngl` and `numpy`+`pyrr` to draw sprite-based
games in Python. This repository currently serves as an example of how to do
this. This README is a walk-through of the code so far.

Using modern OpenGL (4.0+) lets us use shaders and frame-buffer objects for
a full range of effects.

Pygame's graphics system uses software rendering by default. However we can
avoid using that, and just use the features that complement working with
OpenGL operations. Pygame can:

* Create a window with an OpenGL context
* Handle input
* Load images and prepare textures
* Play sounds

# Initialising a context

We need Pygame 2.0 to be able to request an OpenGL 4.0 Core context (the
`GL_CONTEXT_MAJOR_VERSION` flags are new):

```python
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
```

## Packing a texture atlas

Each sprite we want to render needs to be in a texture. However to efficiently
render many different sprites we need to put many sprites into a single
texture. Then we use texture coordinates to pick the correct sprite to draw.

To do this we need to solve the rectangle bin packing problem, which is NP-hard
to solve completely, but for which there are good heuristics. A good paper on
many of the approaches that exist is *A Thousand Ways to Pack The Bin: A
Practical Approach to Rectangle Bin Packing* (Jylänki, 2010)
([pdf](https://github.com/juj/RectangleBinPack/blob/master/RectangleBinPack.pdf),
[github](https://github.com/juj/RectangleBinPack)]).


However, implementations are already available.
[rectpack](https://github.com/secnot/rectpack/) is a Python library that
implements most of the algorithms in that paper.

First we allocate some bins. Let's allow 10 512x512 textures:

```python
self.packer = rectpack.newPacker()
self.packer.add_bin(512, 512, count=10)
```

Then load the sprites with Pygame and add them to the packer, and pack them.
We add a couple of pixels of padding around each sprite which prevents them
bleeding into each other over the first couple of mip levels:


```python
for sprite in sprites:
    img = pygame.image.load(spritename)
    pad = self.padding * 2
    w, h = img.get_size()
    self.packer.add_rect(w + pad, h + pad, (img, spritename))

self.packer.pack()
```

Then, we have a solution - we just need to build the textures and save out
the texture coordinates. The code allows the packer to rotate textures for
potentially a better fit, but let's trim that for brevity.

Allocate Pygame surfaces for the bins we used:

```python
n_texs = len(self.packer)
self.surfs = [
    pygame.Surface((512, 512), pygame.SRCALPHA, depth=32)
    for _ in range(n_texs)
]
```

Blit the loaded sprites into the surfaces, and hold onto texture coordinates.
We may as well create the vertices here also. Vertices have an extra `z` value
of 1 which lets us translate them using a 3x3 matrix:


```python
for bin, x, y, w, h, (img, spritename) in self.packer.rect_list():
    orig_w, orig_h = img.get_size()
    dest = self.surfs[bin]
    dest.blit(img, (x + self.padding, y + self.padding))

    l = (x + self.padding) / 512
    t = 1.0 - (y + self.padding) / 512
    r = (x + w - self.padding) / 512
    b = 1.0 - (y + h - self.padding) / 512

    texcoords = np.array([l, t, r, t, r, b, l, b], dtype='f4')
    verts = np.array([
        (0, orig_h, 1),
        (orig_w, orig_h, 1),
        (orig_w, 0, 1),
        (0, 0, 1),
    ], dtype='f4')
    verts -= (orig_w / 2, orig_h / 2, 0)  # center the sprite
    self.tex_for_name[spritename] = (bin, texcoords, verts)

```

Finally, we send the surfaces to the GPU:

```python
self.texs = []
for t in self.surfs:
    tex = ctx.texture(
        t.get_size(),
        4,
        data=pygame.image.tostring(t, "RGBA", 1),
    )
    tex.build_mipmaps(max_level=2)
    self.texs.append(tex)
```


## Shaders

In OpenGL 4+ you always need a GLSL program to render anything.

The vertex program simply multiplies the input coordinate by a view/projection
matrix, which represents our camera/viewport.

The texture coordinates (`uv`) are handed straight to the fragment program.

```glsl
#version 330

uniform mat4 proj;

in vec3 in_vert;
in vec2 in_uv;
out vec2 uv;

void main() {
    gl_Position = proj * vec4(in_vert.xy, 0.0, 1.0);
    uv = in_uv;
}
```

The fragment program does nothing except look up what color to draw from our
texture:

```glsl
#version 330

out vec4 f_color;
in vec2 uv;
uniform sampler2D tex;

void main() {
    f_color = texture(tex, uv);
}
```

## Rendering a frame

To render anything, first we need to create a vertex array object (VAO) that
represents a quad. Each VAO is made up of several vertex buffer objects (VBOs).

Here we have:

* Vertex indices. `GL_QUADS` are no longer a thing so while we are passing 4
  vertices we need to draw them as 2 triangles, so 6 indices.
* Vertices, each one represented by 3 floats.
* Tex corordinates, each one represented by 2 floats.


```python
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
```

To render this is very simply (we just have to bind the texture to unit 0) and
tell the program that `tex` will come from unit 0.

```python
def render(t, dt):
    ctx.clear(1.0, 1.0, 1.0)
    tex.use(0)
    prog['tex'].value = 0
    vao.render()
```

But first, some set-up. We need the projection matrix for the shader:

```python
proj = Matrix44.orthogonal_projection(
    left=0, right=800, top=600, bottom=0, near=-1000, far=1000,
).astype('f4')
prog['proj'].write(proj.tobytes())
```

And we need to enable alpha blending:

```python
ctx.enable(moderngl.BLEND)
ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
```

The game loop is a very standard Pygame loop:

```python
clock = pygame.time.Clock()
t = 0
while True:
    dt = clock.tick(60) / 1000.0
    t += dt
    for ev in pygame.event.get():
        #print(ev)
        if ev.type == pygame.QUIT:
            sys.exit(0)

    keys = pygame.key.get_pressed()
    render(t, dt)
    pygame.display.flip()
```

Which just leaves us with some logic for moving the ship around. We'll do that
by constructing (separate) rotation and translate matrices. We'll initialize
both as an identity:

```python
ship_pos = Vector3()
ship_v = Vector3()
xlate = np.identity(3, dtype='f4')
rot = ident_rot = np.identity(3, dtype='f4')
Z = vector3.create_unit_length_z()
```

The ship we can move in response to keys:

```python
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
xlate[2][:2] = ship_pos[:2]
```

We rotate the ship in the direction is is moving. I could convert the ship's
velocity to an angle, and generate a new rotation matrix for that angle, but
this would involve `sin()` and `cos()` calls which we actually don't need.
The rotation can be constructed just from three basis vectors. Forward (*+x*)
is one basis vector, and *z* never changes. So *y* can be *x* × *z*:

```python
if vector3.length(ship_v):
    rx = vector3.normalize(ship_v)
    ry = vector3.cross(rx, Z)
    rot[0] = rx
    rot[1] = ry
```

Finally, every frame, we send the new vertices to the GPU:

```python
vbo.write(vs @ (rot @ xlate))
```
