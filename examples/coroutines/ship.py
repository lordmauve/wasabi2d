import math
import random
import wasabi2d as w2d
from wasabi2d import clock, vec2, animate


scene = w2d.Scene()
trail = scene.layers[-1].add_particle_group(max_age=2, grow=0.1)
bottomright = vec2(scene.width, scene.height)
center = bottomright / 2

ship = scene.layers[0].add_sprite(
    'ship',
    pos=center
)


async def drive_ship():
    while True:
        x, y = ship.pos
        target = vec2(
            random.uniform(50, scene.width - 50),
            random.uniform(50, scene.height - 50),
        )

        dist, angle = (target - ship.pos).to_polar()
        duration = (dist / 500) ** 0.5

        # Rotate to face
        await animate(ship, duration=0.5, angle=angle)

        # Begin emitting particles
        clock.coro.run(thrust(duration * 0.8))

        # Move
        scene.layers[0].set_effect('trails', fade=1e-2)
        await animate(
            ship,
            duration=duration,
            tween='accel_decel',
            pos=target,
        )
        scene.layers[0].clear_effect()


async def thrust(duration):
    """Fire a little burst of thrust."""
    prev_pos = ship.pos
    async for _ in clock.coro.frames(seconds=duration):
        v = ship.pos - prev_pos
        num = v.length() // 50
        if num:
            trail.emit(
                num,
                pos=ship.pos,
                vel=v.scaled_to(-100),
                vel_spread=10,
                size=3,
                color='#80ffff',
            )


clock.coro.run(drive_ship())
w2d.run()
