import math
import numpy as np
from dataclasses import dataclass
from typing import Any

import wasabi2d as w2d
from wasabi2d.keyboard import keyboard, keys


scene = w2d.Scene(width=1280, height=720, background="#ccaa88")

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
            self.primitive.angle -= self.turn * dt
        elif keyboard.right:
            self.primitive.angle += self.turn * dt

        displacement = self.speed * dt
        self.primitive.pos += displacement * self.forward_vector()

    __basis = np.array([np.pi / 2, 0], dtype=np.float32)

    def forward_vector(self) -> np.ndarray:
        """Get a unit vector in the forward direction."""
        return np.sin(
            self.__basis + (self.primitive.angle + self.primitive_forward)
        )


tank_control = DrivingController(tank, primitive_forward=math.pi / 2)


@w2d.event
def update(dt):
    tank_control.update(dt)


w2d.run()
