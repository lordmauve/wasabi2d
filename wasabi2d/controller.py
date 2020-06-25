"""Gamepad and controller support for Wasabi2D.

We provide a much more abstract interface over controllers than Pygame itself,
so that we can supply keyboard keys and map axes.

Sketch of the API:

    class Controller(w2d.Controller):
        dpad = w2d.Controls.DPad()
        shoot = w2d.Controls.AcceptButton()


    player1 = Controller()
    print(player1.dpad)  # prints (0, 0)
    print(player1.shoot)  # prints False


    @player1.on_shoot_pressed
    def func():
        ...


Types of control that can be requested:

    DPAD = 0
    STICK = 1
    ACCEPT_BUTTON = 2
    CANCEL_BUTTON = 3
    BUTTON = 4

"""
from dataclasses import dataclass
import pygame.joystick

from pygame.math import Vector2

from .keyboard import keyboard
from .constants import keys


_sticks = []


def reload_joysticks():
    """Reload the list of joysticks."""
    pygame.joystick.quit()
    pygame.joystick.init()
    _sticks.clear()
    for i in range(pygame.joystick.get_count()):
        stick = pygame.joystick.Joystick(i)
        stick.init()
        _sticks.append(stick)


class Controller:
    """An abstract controller."""

    def __init__(self, **kwargs):
        self._stick = get_stick()
        self._key_bindings = {}
        self.__dict__.update(kwargs)

    def release(self):
        """Release the stick."""
        release_stick(self._stick)


CURSOR_KEY_SETS = [
    (keys.UP, keys.LEFT, keys.DOWN, keys.RIGHT),
    (keys.W, keys.A, keys.S, keys.D),
    (keys.I, keys.J, keys.K, keys.L),
]


next_stick = 0
free_sticks = set()


def reset():
    """Reset the leases for sticks."""
    global next_stick
    next_stick = 0
    free_sticks.clear()


def get_stick() -> int:
    """Get the next available stick.

    This function will never fail to allocate a stick, which is useful if
    sticks are not attached at the start of the game.

    """
    global next_stick
    if free_sticks:
        s = min(free_sticks)
        free_sticks.discard(s)
    else:
        s = next_stick
        next_stick += 1
    return s


def release_stick(id: int):
    """Release the given stick."""
    free_sticks.add(id)


# Mapping of connected sticks
_sticks = {}


@dataclass(eq=False)
class DPad:
    """Descriptor for accessing a stick axis."""
    #: If True, treat the diagonals as (√½, √½) instead of (1, 1)
    normalize: bool = False

    def __get__(self, inst, cls):
        stick = _sticks.get(inst._stick)

        x = y = 0
        if stick:
            xaxis, yaxis = inst._stick_bindings[self]
            x = round(stick.get_axis(xaxis))
            y = round(stick.get_axis(yaxis))

        keybindings = inst._key_bindings.get(self)
        if keybindings:
            up, left, down, right = keybindings
            if not x:
                if keyboard[left]:
                    x = -1
                elif keyboard[right]:
                    x = 1
            if not y:
                if keyboard[up]:
                    y = -1
                elif keyboard[down]:
                    y = 1

        v = Vector2(x, y)
        if self.normalize and x and y:
            v.normalize_ip()
        return v


@dataclass(eq=False)
class Stick:
    """An analogue stick.

    On access this computes a normalized vector. A central dead zone is mapped
    to the zero vector so that releasing the stick gives no input, even with
    imperfect analogue input.

    """
    dead_zone: float = 0.1
    saturation: float = 0.95

    def __get__(self, inst, cls):
        stick = _sticks.get(inst._stick)

        x = y = 0
        if stick:
            xaxis, yaxis = inst._stick_bindings[self]
            x = stick.get_axis(xaxis)
            y = stick.get_axis(yaxis)
            v = Vector2(x, y)
            length = v.length()
            if length < self.dead_zone:
                return Vector2(0, 0)
            else:
                range = self.saturation - self.dead_zone
                scale = min(
                    1.0,
                    (length - self.dead_zone) / range
                ) / length
                return v * scale

