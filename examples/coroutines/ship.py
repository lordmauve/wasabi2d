import math
import random
from wasabi2d import Scene, clock, run, Vector2


scene = Scene()
ship = scene.layers[0].add_sprite(
    'ship',
    pos=(scene.width / 2, scene.height / 2)
)


async def drive_ship():
    while True:
        x, y = ship.pos
        tx = random.uniform(50, scene.width - 50)
        ty = random.uniform(50, scene.height - 50)

        dx = tx - x
        dy = ty - y
        angle = math.atan2(dy, dx)
        dist = math.hypot(dx, dy)

        async for angle in clock.coro.interpolate(ship.angle, angle, 0.5):
            ship.angle = angle

        scene.layers[0].set_effect('trails', fade=1e-3)
        async for pos in clock.coro.interpolate(
            (x, y),
            (tx, ty),
            duration=(dist / 500) ** 0.5,
            tween='accel_decel',
        ):
            ship.pos = pos
        scene.layers[0].clear_effect()



clock.coro.run(drive_ship())
run()

