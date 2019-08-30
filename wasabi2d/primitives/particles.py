from typing import Tuple, Any
from functools import partial

import numpy as np
import numpy.random
import moderngl

from ..color import convert_color
from ..allocators.vertlists import VAO
from .circles import color_vao


PARTICLE_PROGRAM = dict(
    vertex_shader='''
        #version 330

        in vec2 in_vert;
        in vec4 in_color;
        in float in_size;
        out vec4 g_color;
        out float size;

        void main() {
            gl_Position = vec4(in_vert, 0.0, 1.0);
            g_color = in_color;
            size = in_size;
        }
    ''',
    geometry_shader="""
#version 330 core
layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

in vec4 g_color[];
in float size[];
out vec4 color;

uniform mat4 proj;

void main() {
    color = g_color[0];
    float sz = size[0] * 0.5;
    vec2 pos = gl_in[0].gl_Position.xy;

    gl_Position = proj * vec4(pos.x - sz, pos.y + sz, 0.0, 1.0);
    EmitVertex();

    gl_Position = proj * vec4(pos.x + sz, pos.y + sz, 0.0, 1.0);
    EmitVertex();

    gl_Position = proj * vec4(pos.x - sz, pos.y - sz, 0.0, 1.0);
    EmitVertex();

    gl_Position = proj * vec4(pos.x + sz, pos.y - sz, 0.0, 1.0);
    EmitVertex();

    EndPrimitive();
}
""",
    fragment_shader='''
        #version 330

        out vec4 f_color;
        in vec4 color;

        void main() {
            f_color = color;
        }
    ''',
)


def particles_vao(
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a VAO for rendering particles."""
    return VAO(
        mode=moderngl.POINTS,
        ctx=ctx,
        prog=shadermgr.get(**PARTICLE_PROGRAM),
        dtype=np.dtype([
            ('in_vert', '2f4'),
            ('in_color', '4f4'),
            ('in_size', 'f4'),
        ])
    )


class ParticleGroup:
    """A group of particles."""

    def __init__(
            self,
            layer,
            *,
            grow: float = 1.0,
            max_age: float = np.inf,
            fade: float = 1.0):
        super().__init__()
        self.layer = layer
        self.num: int = 0  # Number of particles we have
        self.max_age = max_age
        self.fade = fade
        self.grow = grow
        self.ages = np.zeros([0])
        self.vels = np.zeros([0, 2])

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
            size_spread: float = 0.0):
        """Emit num particles."""
        num = round(num)
        color = convert_color(color)

        prev_verts = self.lst.vertbuf
        alive = self.ages < self.max_age
        num_alive = np.sum(alive)
        need = num_alive + num

        verts_alive = prev_verts[alive]

        self.lst.realloc(need, need)
        self.lst.indexbuf[:] = np.arange(need, dtype='u4')

        new_vel = np.random.normal(vel, vel_spread, [num, 2])
        new_pos = np.random.normal(pos, pos_spread, [num, 2])
        new_size = np.random.normal(size, size_spread, num)

        verts = self.lst.vertbuf
        self.ages = np.hstack([self.ages[alive], [0] * num])
        self.vels = np.vstack([self.vels[alive], new_vel])
        verts[:num_alive] = verts_alive
        verts[num_alive:]['in_color'] = color
        verts[num_alive:]['in_vert'] = new_pos
        verts[num_alive:]['in_size'] = new_size
        self.lst.dirty = True

    def _compact(self):
        alive = self.ages < self.max_age
        self.num = num_alive = np.sum(alive)
        verts_alive = self.lst.vertbuf[alive]
        self.lst.realloc(num_alive, num_alive)
        self.lst.indexbuf[:] = np.arange(num_alive, dtype='u4')
        self.ages = self.ages[alive].copy()
        self.vels = self.vels[alive].copy()
        self.lst.vertbuf[:] = verts_alive

    def _update(self, t, dt):
        self._compact()

        # Update
        self.ages += dt
        self.lst.vertbuf['in_vert'] += self.vels * dt
        self.lst.vertbuf['in_color'] *= self.fade ** dt
        self.lst.vertbuf['in_size'] *= self.grow ** dt
        self.lst.dirty = True

    def _migrate(self, vao: VAO):
        """Migrate the particles into the given VAO."""
        self.vao = vao
        num = max(self.num, 1024)
        idxs = np.arange(num, dtype='u4')
        # Allocate a large slice (set high water mark)
        self.lst = vao.alloc(num, num)
        self.lst.indexbuf[:] = idxs

        # Realloc to how much we actually want
        self.lst.realloc(self.num, self.num)

    def delete(self):
        self.layer.objects.discard(self)
        self.layer._dynamic.discard(self)
        self.lst.delete()
