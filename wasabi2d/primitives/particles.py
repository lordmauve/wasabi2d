from typing import Tuple, Any
from functools import partial

import numpy as np
import numpy.random
import moderngl

from ..color import convert_color
from ..allocators.vertlists import VAO
from .circles import color_vao


#: Constructor for a VAO for rendering points
points_vao = partial(color_vao, moderngl.POINTS)


class ParticleGroup:
    """A group of particles."""

    def __init__(
            self,
            layer,
            *,
            max_age: float = np.inf,
            fade: float = 1.0):
        super().__init__()
        self.layer = layer
        self.num: int = 0  # Number of particles we have
        self.max_age = max_age
        self.fade = fade
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
            color: Any = (1, 1, 1, 1)):
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

        verts = self.lst.vertbuf
        self.ages = np.hstack([self.ages[alive], [0] * num])
        self.vels = np.vstack([
            self.vels[alive],
            new_vel,
        ])
        verts[:num_alive] = verts_alive
        verts[num_alive:]['in_color'] = color
        verts[num_alive:]['in_vert'] = new_pos
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
