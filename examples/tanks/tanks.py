import math
import numpy as np
from dataclasses import dataclass
from typing import Any

import wasabi2d as w2d
from wasabi2d.keyboard import keyboard, keys


scene = w2d.Scene(
    width=1280,
    height=720,
    background="#ccaa88",
)

tilemap = scene.layers[0].add_tile_map()
tilemap.fill_rect(
    'sand_base_1',
    left=0,
    right=scene.width // 64 + 1,
    top=0,
    bottom=scene.height // 64 + 1,
)
tilemap.line(
    'sand_road_lr',
    (2, 1),
    (20, 1)
)
tilemap.line(
    'sand_road_ud',
    (1, 2),
    (1, 8),
)
tilemap.line(
    'sand_road_lr',
    (2, 9),
    (20, 9)
)

tilemap[1, 1] = 'sand_road_dr'
tilemap[1, 4] = 'sand_road_udr'
tilemap.line('sand_road_ld', (2, 4), (6, 8))
tilemap.line('sand_road_ur', (2, 5), (6, 9))
tilemap[1, 9] = 'sand_road_ur'


tilemap.flood_fill(
    ['grass_base_1', 'grass_base_2'],
    (2, 6)
)


scene.layers[1].set_effect('dropshadow', offset=(2, 2))
tank = scene.layers[1].add_sprite('tank_green', pos=(50, 50))
tank.speed = 0


@dataclass
class DrivingController:
    """Control driving an object around."""
    primitive: Any

    #: Acceleration when a key is pressed, in pixels per second
    acceleration: float = 200.0

    #: Fraction of speed retained per frame
    drag: float = 0.1

    #: Rate of turn, in radians/second
    turn: float = 1.5

    #: key bindings
    forward_key: keys = keys.UP
    reverse_key: keys = keys.DOWN
    left_key: keys = keys.LEFT
    right_key: keys = keys.RIGHT

    #: The angle that is "forward" relative to the primitive
    primitive_forward: float = 0.0

    #: The speed of the object. This is maintained by the controller but
    #: can be updated (eg. on collision)
    speed: float = 0.0

    def update(self, dt: float = 1 / 60):
        """Update the primitive."""
        self.speed *= self.drag ** dt
        if keyboard.up:
            self.speed += self.acceleration * dt
        elif keyboard.down:
            self.speed -= self.acceleration * dt

        if keyboard.left:
            self.primitive.angle -= np.copysign(self.turn * dt, self.speed)
        elif keyboard.right:
            self.primitive.angle += np.copysign(self.turn * dt, self.speed)

        displacement = self.speed * dt
        self.primitive.pos += displacement * self.forward_vector()

    __basis = np.array([np.pi / 2, 0], dtype=np.float32)

    def forward_vector(self) -> np.ndarray:
        """Get a unit vector in the forward direction."""
        return np.sin(
            self.__basis + (self.primitive.angle + self.primitive_forward)
        )


tank_control = DrivingController(
    tank,
    acceleration=500,
    primitive_forward=math.pi / 2
)


@w2d.event
def update(dt):
    tank_control.update(dt)
    scene.camera.pos = tank.pos


w2d.run()
