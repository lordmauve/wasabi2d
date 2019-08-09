"""wasabi2d, a 2D game engine using moderngl, pygame and numpy."""

from .atlas import Atlas
from .layers import LayerGroup
from .game import EventMapper
from .constants import keys, mouse
from .loaders import sounds
from . import music

event = EventMapper()
del EventMapper

run = event.run
