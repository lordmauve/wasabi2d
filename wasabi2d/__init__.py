"""wasabi2d, a 2D game engine using moderngl, pygame and numpy."""
import os

# Don't show Pygame's annoying message because while I might use PyGame,
# I don't appreciate libraries I use communicating with my users.
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from wasabigeom import vec2
from .game import EventMapper
from .constants import keys, mouse, keymods
from .loaders import sounds
from . import music
from . import clock
from . import tone
from .scene import Scene, Window
from .animation import animate
from .storage import Storage
from .chain import LayerRange
from .primitives.group import Group
from .loop import do, run, PygameEvents, gather, Nursery, Event

# Vector2 was pygame.math.Vector2, which was mutable, so we replaced it with
# something immutable and faster. Maybe this will work in some cases because
# they're not crazy dissimilar, and anyway this was never documented in the
# first place.
Vector2 = vec2

event = EventMapper()
events = PygameEvents(event)
next_event = events.wait
do(events.run())
del EventMapper
del PygameEvents

__version__ = (1, 4, 0)
__all__ = [
    'Vector2',
    'event',
    'run',
    'keys', 'mouse', 'keymods',
    'sounds', 'music', 'tone',
    'clock', 'animate',
    'Scene', 'Storage', 'LayerRange',
    'Group',
    'gather', 'Nursery', 'Event',
]
