"""Tests for controller configurations."""
from dataclasses import dataclass, field
from copy import deepcopy
from typing import List
from contextlib import contextmanager
from unittest.mock import patch

import pygame.joystick

from wasabi2d.constants import keys
from wasabi2d.keyboard import keyboard
from wasabi2d import controller


def mutfield(default):
    """Field with a mutable default."""
    return field(
        default_factory=lambda: deepcopy(default)
    )


@dataclass
class FakeJoystick:
    """Stand-in for the pygame Joystick class."""
    id: int
    was_init: bool = False

    name: str = "Fake Joystick"
    axes: List[float] = mutfield([0, 0])
    buttons: List[bool] = mutfield([False] * 4)

    def init(self):
        self.was_init = True

    def quit(self):
        self.was_init = False

    def get_init(self) -> bool:
        return self.was_init

    def get_id(self) -> int:
        return self.id

    def get_name(self) -> str:
        return self.NAME

    def get_numaxes(self) -> int:
        return len(self.axes)

    def get_axis(self, axis_number: int) -> float:
        return self.axes[0]

    def get_numbuttons(self) -> int:
        return len(self.buttons)

    def get_button(self, button: int) -> bool:
        return self.buttons[button]

    # And we'll ignore hats and balls for now


@contextmanager
def with_sticks(n):
    """Patch the number of joysticks."""
    sticks = [FakeJoystick(i) for i in range(n)]
    controller.reset()
    keyboard._pressed.clear()
    with patch.multiple(
            'pygame.joystick',
            get_count=len(sticks),
            Joystick=lambda id: sticks[id]):
        yield


@with_sticks(1)
def test_get_stick():
    """Regardless of how many sticks are attached, we can allocate sticks."""
    sticks = [controller.get_stick() for _ in range(3)]
    assert sticks == [0, 1, 2]


@with_sticks(1)
def test_release_stick():
    """We can release sticks and obtain them again."""
    stick1 = controller.get_stick()
    stick2 = controller.get_stick()
    controller.release_stick(stick1)
    stick1 = controller.get_stick()
    assert [stick1, stick2] == [0, 1]


@with_sticks(2)
def test_controller_dpad():
    """We can build a controller that receives DPad input."""
    class MyController(controller.Controller):
        pad = controller.DPad()

    c = MyController()
    assert c.pad == (0, 0)


@with_sticks(2)
def test_controller_dpad_input():
    """We can get input via the D-pad."""
    class MyController(controller.Controller):
        pad = controller.DPad()

    c = MyController()
    assert c._stick == 0

    stick = pygame.joystick.Joystick(0)
    stick.axes[0] = 0.95
    stick.axes[1] = 0.95

    assert c.pad == (1, 1)


@with_sticks(2)
def test_controller_key_input():
    """The keyboard is also mapped to a controller."""
    class MyController(controller.Controller):
        pad = controller.DPad()

    c = MyController()
    keyboard._pressed.add(keys.UP)
    assert c.pad == (0, -1)
