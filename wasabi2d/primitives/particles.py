from typing import Tuple, Any, Optional
from dataclasses import dataclass

import numpy as np
import numpy.random
from sortedcontainers import SortedList

from .base import Transformable
from ..clock import default_clock
from ..color import convert_color
from ..allocators.vertlists import VAO


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

    def render(self, camera):
        self.prog['grow'].value = self.pgroup.grow
        self.prog['max_age'].value = self.pgroup.max_age
        self.prog['tex'].value = 0
        self.prog['color_tex'].value = 1
        self.tex.use(0)
        self.color_tex.use(1)
        super().render(camera)


class ParticleGroup:
    """A group of particles."""

    def __init__(
            self,
            layer,
            clock=default_clock,
            *,
            grow: float = 1.0,
            max_age: float = np.inf,
            gravity: Tuple[float, float] = (0, 0),
            drag: float = 1.0,
            spin_drag: float = 1.0):
        super().__init__()
        self.layer = layer
        self.num: int = 0  # Number of particles we have
        self.max_age = max_age
        self.grow = grow
        self.gravity = np.array(gravity)
        self.drag = drag
        self.spin_drag = spin_drag
        self.spins = np.zeros([0])
        self.vels = np.zeros([0, 2])
        self._color_stops = SortedList()
        self.color_tex = layer.ctx.texture((512, 1), 4, dtype='f2')
        self.color_vals = np.ones((512, 4), dtype='f2')
        self.color_tex.write(self.color_vals)
        self.emitters = set()
        self._clock = clock
        clock.each_tick(self._update)

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
            angle: float = 0.0,
            angle_spread: float = 0.0):
        """Emit num particles."""
        num = round(num)
        if num == 0:
            return
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
        new_angles = np.random.normal(angle, angle_spread, num)
        new_spins = np.random.normal(spin, spin_spread, num)

        verts = self.lst.vertbuf
        self.vels = np.vstack([self.vels[alive], new_vel])
        self.spins = np.hstack([self.spins[alive], new_spins])
        verts[:num_alive] = verts_alive
        new = verts[num_alive:]
        new['in_age'] = 0
        new['in_color'] = color
        new['in_size'] = new_size
        new['in_vert'] = new_pos
        new['in_angle'] = new_angles
        self.lst.dirty = True

    def _compact(self):
        alive = self.lst.vertbuf['in_age'] < self.max_age
        self.num = num_alive = np.sum(alive)
        verts_alive = self.lst.vertbuf[alive]
        self.lst.realloc(num_alive, num_alive)

        first_vertex = self.lst.vertoff.start
        self.lst.indexbuf[:] = np.arange(
            first_vertex,
            first_vertex + num_alive,
            dtype='u4'
        )
        self.vels = self.vels[alive].copy()
        self.spins = self.spins[alive].copy()
        self.lst.vertbuf[:] = verts_alive

    def _update(self, dt):
        self.lst.vertbuf['in_age'] += dt
        self._compact()

        # Update
        orig_vels = self.vels
        self.vels *= self.drag ** dt
        self.vels += self.gravity * dt
        self.spins *= self.spin_drag ** dt

        self.lst.vertbuf['in_vert'] += (self.vels + orig_vels) * (dt * 0.5)
        self.lst.vertbuf['in_angle'] += self.spins * dt
        self.lst.dirty = True

        for e in self.emitters:
            e._emit(dt)

    def _migrate(self, vao: VAO):
        """Migrate the particles into the given VAO."""
        self.vao = vao
        num = max(self.num, 1024)

        # Allocate a large slice (set high water mark)
        self.lst = vao.alloc(num, num)
        first_vertex = self.lst.vertoff.start
        self.lst.indexbuf[:] = np.arange(
            first_vertex,
            first_vertex + num,
            dtype='u4'
        )

        # Realloc to how much we actually want
        self.lst.realloc(self.num, self.num)

    def add_emitter(self, **kwargs):
        """Add a particle emitter object."""
        e = Emitter(self, **kwargs)
        self.emitters.add(e)
        return e

    def delete(self):
        self.layer.objects.discard(self)
        self._clock.unschedule(self._update)
        self.lst.free()


@dataclass
class EmitterDesc:
    """Descriptor for an emitter property."""
    default: Any = 0.0
    name: Optional[str] = None

    def __set_name__(self, cls, name):
        if self.name is None:
            self.name = name

    def __get__(self, inst, cls):
        return inst._params.get(self.name, self.default)

    def __set__(self, inst, value):
        inst._params[self.name] = value


class Emitter(Transformable):
    """A transformable emitter object."""

    group: ParticleGroup
    pos_spread: float = EmitterDesc(0)
    vel: Tuple[float, float] = (0, 0)
    vel_spread: float = EmitterDesc(0)
    color: Any = EmitterDesc((1, 1, 1, 1))
    size: float = EmitterDesc(1.0)
    size_spread: float = EmitterDesc(0.0)
    spin: float = EmitterDesc(0.0)
    spin_spread: float = EmitterDesc(0.0)
    emit_angle: float = 0.0
    emit_angle_spread: float = EmitterDesc(0.0, 'angle_spread')

    def __init__(
        self,
        group: ParticleGroup,
        *,
        rate: float = 100.0,
        pos: Tuple[float, float] = (0, 0),
        angle: float = 0.0,
        scale: float = 1.0,
        **kwargs,
    ):
        super().__init__()
        self._group = group
        self._params = {}
        self.rate = rate

        self.pos = pos
        self.angle = angle
        self.scale = scale

        self._vecs = np.array([
            [0, 0, 1],
            [*self.vel, 0],
            [1, 0, 0],
        ], dtype=np.float32)

        for k, v in kwargs.items():
            if k not in type(self).__dict__:
                raise TypeError(
                    f"{type(self).__name__}.__init__() does not accept a "
                    f"keyword argument {k}!r"
                )
            setattr(self, k, v)

    def delete(self):
        """Delete the emitter."""
        self._group.emitters.discard(self)

    def _set_dirty(self):
        """We don't need to track dirtyiness."""

    def _emit(self, dt):
        """Emit particles in the group."""
        num = np.random.poisson(self.rate * dt)

        if num == 0:
            return

        xform = self._xform()[:, :2]

        self._vecs[1, :2] = self.vel
        pos, vel, (rotx, roty) = self._vecs @ xform
        angle = np.arctan2(roty, rotx) + self.emit_angle

        self._group.emit(
            num,
            pos=pos,
            vel=vel,
            angle=angle,
            **self._params
        )
