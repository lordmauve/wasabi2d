"""wasabi2d, a 2D game engine using moderngl, pygame and numpy."""
import os

# Don't show Pygame's annoying message because while I might use PyGame,
# I don't appreciate libraries I use communicating with my users.
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from pygame.math import Vector2
from .game import EventMapper
from .constants import keys, mouse, keymods
from .loaders import sounds
from . import music
from . import clock
from . import tone
from .scene import Scene
from .animation import animate
from .storage import Storage
from .chain import LayerRange
from .primitives.group import Group

event = EventMapper()
del EventMapper

run = event.run

__version__ = (1, 4, 0)
__all__ = [
    'Vector2',
    'event',
    'run',
    'keys', 'mouse', 'keymods',
    'sounds', 'music', 'tone',
    'clock', 'animate',
    'Scene', 'Storage', 'LayerRange',
    'Group'
]
