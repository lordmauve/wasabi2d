from typing import Tuple, Any

import numpy as np
import numpy.random
from sortedcontainers import SortedList

from ..color import convert_color
from ..allocators.vertlists import VAO


PARTICLE_PROGRAM = dict(
    vertex_shader='''
        #version 330

        in vec2 in_vert;
        in vec4 in_color;
        in float in_size;
        in float in_angle;
        in float in_age;
        out vec4 g_color;
        out float size;
        out float age;
        out mat2 rots;

        uniform float max_age;

        void main() {
            gl_Position = vec4(in_vert, 0.0, 1.0);
            g_color = in_color;
            size = in_size;
            age = in_age;

            float c = cos(in_angle);
            float s = sin(in_angle);
            rots = mat2(c, -s, s, c);
        }
    ''',
    geometry_shader="""
#version 330 core
layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

in mat2 rots[];
in vec4 g_color[];
in float size[];
in float age[];
out vec4 color;
out vec2 uv;

uniform mat4 proj;
uniform sampler2D color_tex;
uniform float max_age;
uniform float grow;

void main() {
    float age_frac = clamp(age[0] / max_age, 0.0, 511.0 / 512.0);
    color = g_color[0] * texture(color_tex, vec2(age_frac, 0.0));
    vec2 pos = gl_in[0].gl_Position.xy;
    mat2 rot = rots[0];

    float sz = size[0] * pow(grow, age[0]);

    // Vector to the corner
    vec2 corners[4] = vec2[4](
        vec2(-sz, sz),
        vec2(sz, sz),
        vec2(-sz, -sz),
        vec2(sz, -sz)
    );
    vec2 uvs[4] = vec2[4](
        vec2(0, 1),
        vec2(1, 1),
        vec2(0, 0),
        vec2(1, 0)
    );

    for (int i = 0; i < 4; i++) {
        gl_Position = proj * vec4(pos + rot * corners[i], 0.0, 1.0);
        uv = uvs[i];
        EmitVertex();
    }
    EndPrimitive();
}
""",
    fragment_shader='''
        #version 330

        out vec4 f_color;
        in vec4 color;
        in vec2 uv;
        uniform sampler2D tex;

        void main() {
            f_color = color * texture(tex, uv);
        }
    ''',
)

PARTICLE_DTYPE = np.dtype([
    ('in_vert', '2f4'),
    ('in_color', '4f4'),
    ('in_age', 'f4'),
    ('in_size', 'f4'),
    ('in_angle', 'f4'),
])


class ParticleVAO(VAO):
    """A VAO with an image texture and a color ramp texture."""

    def __init__(self, pgroup, *args, **kwargs):
        super().__init__(*args, dtype=PARTICLE_DTYPE, **kwargs)
        self.pgroup = pgroup

    def render(self):
        self.prog['grow'].value = self.pgroup.grow
        self.prog['max_age'].value = self.pgroup.max_age
        self.prog['tex'].value = 0
        self.prog['color_tex'].value = 1
        self.tex.use(0)
        self.color_tex.use(1)
        super().render()


class ParticleGroup:
    """A group of particles."""

    def __init__(
            self,
            layer,
            *,
            grow: float = 1.0,
            max_age: float = np.inf,
            gravity: Tuple[float, float] = (0, 0),
            drag: float = 1.0):
        super().__init__()
        self.layer = layer
        self.num: int = 0  # Number of particles we have
        self.max_age = max_age
        self.grow = grow
        self.gravity = np.array(gravity)
        self.drag = drag
        self.spins = np.zeros([0])
        self.vels = np.zeros([0, 2])
        self._color_stops = SortedList()
        self.color_tex = layer.ctx.texture((512, 1), 4, dtype='f2')
        self.color_vals = np.ones((512, 4), dtype='f2')
        self.color_tex.write(self.color_vals)

    def add_color_stop(self, age, color):
        """Add a color stop for particles of the given age.

        Particles will fade between the colors of the stops as their age
        changes.
        """
        color = convert_color(color)
        self._color_stops.add((age, *color))
        xs = np.linspace(0, self.max_age, 512)

        ages, *colors = zip(*self._color_stops)
        for i in range(4):
            self.color_vals[:, i] = np.interp(
                xs,
                ages,
                colors[i],
            )
        self.color_tex.write(self.color_vals)

    def emit(
            self,
            num: int,
            *,
            pos: Tuple[float, float],
            pos_spread: float = 0,
            vel: Tuple[float, float] = (0, 0),
            vel_spread: float = 0,
            color: Any = (1, 1, 1, 1),
            size: float = 1.0,
            size_spread: float = 0.0,
            spin: float = 0.0,
            spin_spread: float = 0.0,
            ):
        """Emit num particles."""
        num = round(num)
        color = convert_color(color)

        prev_verts = self.lst.vertbuf
        alive = self.lst.vertbuf['in_age'] < self.max_age
        num_alive = np.sum(alive)
        need = num_alive + num

        verts_alive = prev_verts[alive]

        self.lst.realloc(need, need)
        self.lst.indexbuf[:] = np.arange(need, dtype='u4') + self.lst.vertoff.start

        new_vel = np.random.normal(vel, vel_spread, [num, 2])
        new_pos = np.random.normal(pos, pos_spread, [num, 2])
        new_size = np.random.normal(size, size_spread, num)
        new_spins = np.random.normal(spin, spin_spread, num)

        verts = self.lst.vertbuf
        self.vels = np.vstack([self.vels[alive], new_vel])
        self.spins = np.hstack([self.spins[alive], new_spins])
        verts[:num_alive] = verts_alive
        verts[num_alive:]['in_age'] = 0
        verts[num_alive:]['in_color'] = color
        verts[num_alive:]['in_size'] = new_size
        verts[num_alive:]['in_vert'] = new_pos
        self.lst.dirty = True

    def _compact(self):
        alive = self.lst.vertbuf['in_age'] < self.max_age
        self.num = num_alive = np.sum(alive)
        verts_alive = self.lst.vertbuf[alive]
        self.lst.realloc(num_alive, num_alive)
        self.lst.indexbuf[:] = np.arange(num_alive, dtype='u4') + self.lst.vertoff.start
        self.vels = self.vels[alive].copy()
        self.spins = self.spins[alive].copy()
        self.lst.vertbuf[:] = verts_alive

    def _update(self, t, dt):
        self.lst.vertbuf['in_age'] += dt
        self._compact()

        # Update
        orig_vels = self.vels
        self.vels = self.vels * self.drag ** dt + self.gravity * dt

        self.lst.vertbuf['in_vert'] += (self.vels + orig_vels) * (dt * 0.5)
        self.lst.vertbuf['in_angle'] += self.spins * dt
        self.lst.dirty = True

    def _migrate(self, vao: VAO):
        """Migrate the particles into the given VAO."""
        self.vao = vao
        num = max(self.num, 1024)
        idxs = np.arange(num, dtype='u4')
        # Allocate a large slice (set high water mark)
        self.lst = vao.alloc(num, num)
        self.lst.indexbuf[:] = idxs + self.lst.vertoff.start

        # Realloc to how much we actually want
        self.lst.realloc(self.num, self.num)

    def delete(self):
        self.layer.objects.discard(self)
        self.layer._dynamic.discard(self)
        self.lst.delete()
