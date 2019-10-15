import random
import wasabi2d as w2d
from wasabi2d import clock, Vector2, animate


scene = w2d.Scene()
scene.background = '#ccddff'


async def explode(pos):
    """Create an explosion at pos."""
    scene.camera.screen_shake()
    sprite = scene.layers[1].add_sprite('explosion', pos=pos)
    sprite.color = (1, 1, 1, 0)

    animate(
        sprite,
        duration=0.9,
        angle=10,
    )

    # Explode phase
    await animate(
        sprite,
        duration=0.3,
        tween='accelerate',
        scale=3,
        color=(1, 1, 1, 1),
    )

    # Twist phase
    await clock.coro.sleep(0.1)

    # Collapse phase
    await animate(
        sprite,
        duration=0.5,
        scale=1,
        color=(0, 0, 0, 0),
    )

    # Delete it again
    sprite.delete()


async def spawn_explosions():
    """Continue spawning explosions."""
    while True:
        px = random.uniform(50, scene.width - 50)
        py = random.uniform(50, scene.height - 50)
        clock.coro.run(explode((px, py)))
        await clock.coro.sleep(random.uniform(0.5, 3))


clock.coro.run(spawn_explosions())
w2d.run()
