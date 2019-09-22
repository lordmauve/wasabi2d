Particles
=========

Wasabi2d includes a basic particle system that can easily update and render
hundreds of particles. Particles can be textured, move, and change color over
time. Finally they have finite lifetimes after which they are removed.

Particles are always created within a **particle group** which contains some
global parameters that affect particles.

It is intended that you create only one particle group per effect type, then
use it for all particles/emitters for that effect.

.. method:: Layer.add_particle_group(texture: str = None, grow: float = 1.0, max_age: float = np.inf, gravity: Tuple[float, float] = (0, 0), drag: float = 1.0)

    Create a particle group. The parameters correspond to attributes of the
    group object, as documented below.


Particle Group Configuration
----------------------------

.. attribute:: particle_group.texture

    The image used for each particle. Textures must be in a directory named
    ``images/`` and must be named in lowercase with underscores. This
    restriction ensures that games written with wasabi2d will work on with case
    sensitive and insensitive filenames.

    If ``texture`` is ``None``, particles will be drawn as squares.


.. attribute:: particle_group.grow

    A growth rate for particles. The size will change by a factor of ``grow``
    every 1 second. Factors smaller than 1.0 will shrink over time; factors
    greater will grow.


.. attribute:: particle_group.max_age

    The lifetime for particles in seconds. Particles older than this will be
    removed.

    If you don't set this, particles will stick around until you delete the
    group.


.. attribute:: particle_group.gravity

    Global "gravity" vector, ie. constant acceleration applied to all
    particles.

    Vectors that point downwards (eg. ``(0, 100)``) would cause particles to
    fall under gravity.

    Vectors that point upwards (eg. ``(0, -100)``) would cause particles to
    rise, perhaps because they are buoyant.

    Units are pixels per second per second.


.. attribute:: particle_group.drag

    A drag factor.

    All velocities will be multiplied by this factor every second. For example,
    a ``drag`` of ``0.5`` will cause particles to lose half their speed every
    second.

    This will slow particles to a stop, unless they hit their ``max_age``, or
    unless ``gravity`` is set. If gravity is set they will eventually hit a
    "terminal velocity" in the direction of the gravity vector.


.. attribute:: particle_group.spin_drag

    A drag factor for angular velocity (spin).

    All spins will be multiplied by this factor every second.


.. method:: particle_group.add_color_stop(age: float, color: Any)

    Add a color stop for particles at age (in seconds).

    Particles will fade between the colors of the stops as their age
    increases.

    Use multiple stops to create a color gradient. For example, to fade from
    red to transparent after 2s::

        group.add_color_stop(0, (1, 0, 0, 1))
        group.add_color_stop(2, (1, 0, 0, 0))


Emitting particles
------------------

Particle groups don't contain any particles when created. To actually create
particles, call ``.emit()``.


.. automethod:: wasabi2d.primitives.particles.ParticleGroup.emit

    :param num: The number of particles to emit.

    Several parameters configure properties of the particles to emit:

    :param pos: The center position at which to emit particles.
    :param vel: The velocity with with particles will move, in pixels per
                second.
    :param color: A per-emission color for the particles. This will be
                  multiplies with the color ramp configured for the whole
                  particle group.
    :param size: The diameter of the particles to emit, in pixels.
    :param angle: The rotation of the emitted particles, in radians.
    :param spin: The rate of rotation (angular velocity) of particles, in
                 radians per second.

    Several of the above properties are allowed to be randomised over a
    **normal distribution**. The value above gives the mean of the
    distribution. If a ``_spread`` parameter is given it will give the standard
    deviation for the distribution.

    :param pos_spread: The standard deviation for particle positions, in
                       pixels.
    :param vel_spread: The standard deviation for particle velocities, in
                       pixels per second.
    :param size_spread: The standard deviation for particle sizes, in pixels.
    :param angle_spread: The standard deviation for the angle of particles, in
                         radians.
    :param spin_spread: The standard deviation for the rate of rotation of
                        particles, in radians per second.
