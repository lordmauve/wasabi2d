"""wasabi2d, a 2D game engine using moderngl, pygame and numpy."""
import os

# Don't show Pygame's annoying message because while I might use PyGame,
# I don't appreciate libraries I use communicating with my users.
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from pygame.math import Vector2
from .game import EventMapper
from .constants import keys, mouse
from .loaders import sounds
from . import music
from . import clock
from .scene import Scene
from .animation import animate
from .storage import Storage

event = EventMapper()
del EventMapper

run = event.run

__all__ = [
    'Vector2',
    'event',
    'run',
    'keys', 'mouse',
    'sounds', 'music', 'clock', 'animate',
    'Scene', 'Storage',
]
