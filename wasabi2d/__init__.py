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

event = EventMapper()
del EventMapper

run = event.run

__all__ = [
    'Vector2',
    'event',
    'run',
    'keys', 'mouse', 'keymods',
    'sounds', 'music', 'tone',
    'clock', 'animate',
    'Scene', 'Storage', 'LayerRange',
]


LAZY_OBJECTS = {
    'NinePatch': 'wasabi2d.primitives.ninepatch',
}


def __getattr__(k):
    """Expose some objects under this module, but load them lazily

    This will help to reduce start-up time as the package gets larger.

    This method is only used under Python 3.7 but we'll live with that
    for the simplicity of the implementation.

    """
    modname = LAZY_OBJECTS.get(k)
    if not modname:
        raise AttributeError(k)

    import importlib
    mod = importlib.import_module(modname)
    obj = getattr(mod, k)
    globals()[k] = obj
    return obj
