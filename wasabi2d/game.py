import sys
import operator
import time
import types
from collections import namedtuple

import pygame

import wasabi2d.clock
import wasabi2d.keyboard
import wasabi2d.loaders
from . import constants


screen = None  # This global surface is what actors draw to
DISPLAY_FLAGS = 0


def exit():
    """Wait for up to a second for all sounds to play out
    and then exit
    """
    t0 = time.time()
    while pygame.mixer.get_busy():
        time.sleep(0.1)
        if time.time() - t0 > 1.0:
            break
    sys.exit()


def positional_parameters(handler):
    """Get the positional parameters of the given function."""
    code = handler.__code__
    return code.co_varnames[:code.co_argcount]


class DEFAULTICON:
    """Sentinel indicating that we want to use the default icon."""


DrawEvent = namedtuple('DrawEvent', 'type t dt updated')
UpdateEvent = namedtuple('UpdateEvent', 'type t dt keyboard')
ScreenShotEvent = namedtuple('ScreenShotEvent', 'type video')


class EventMapper:
    def __init__(self, get_events=pygame.event.get):
        self.get_events = get_events
        self.keyboard = wasabi2d.keyboard.keyboard
        self.handlers = {}
        self.lock_fps = False

    EVENT_HANDLERS = {
        'on_mouse_down': pygame.MOUSEBUTTONDOWN,
        'on_mouse_up': pygame.MOUSEBUTTONUP,
        'on_mouse_move': pygame.MOUSEMOTION,
        'on_key_down': pygame.KEYDOWN,
        'on_key_up': pygame.KEYUP,
        'on_joybutton_down': pygame.JOYBUTTONDOWN,
        'on_joybutton_up': pygame.JOYBUTTONUP,
        'on_music_end': constants.MUSIC_END,
        'draw': DrawEvent,
        'update': UpdateEvent,
        'on_screenshot_requested': ScreenShotEvent,
    }

    def map_buttons(val):
        return {c for c, pressed in zip(constants.mouse, val) if pressed}

    EVENT_PARAM_MAPPERS = {
        'buttons': map_buttons,
        'button': constants.mouse,
        'key': constants.keys,
    }

    EVENT_PARAM_MAPPERS_JOYSTICK = {
    }

    def __call__(self, handler):
        """Register an event handler."""
        name = handler.__name__
        try:
            type = self.EVENT_HANDLERS[name]
        except KeyError:
            raise KeyError(
                f"Unknown handler type {name}"
            )
        if 'joy' in name:
            mappers = self.EVENT_PARAM_MAPPERS_JOYSTICK
        else:
            mappers = self.EVENT_PARAM_MAPPERS
        self.handlers[type] = self.prepare_handler(handler, mappers)
        return handler

    def prepare_handler(
            self,
            handler: callable,
            param_mappers: dict = EVENT_PARAM_MAPPERS):
        """Adapt a wasabi2d game's raw handler function to take a Pygame Event.

        Returns a one-argument function of the form ``handler(event)``.
        This will ensure that the correct arguments are passed to the raw
        handler based on its argument spec.

        The wrapped handler will also map certain parameter values using
        callables from EVENT_PARAM_MAPPERS; this ensures that the value of
        'button' inside the handler is a real instance of constants.mouse,
        which means (among other things) that it will print as a symbolic value
        rather than a naive integer.

        """
        code = handler.__code__
        if isinstance(handler, types.MethodType):
            start_idx = 1
        else:
            start_idx = 0

        param_names = code.co_varnames[start_idx:code.co_argcount]

        def make_getter(mapper, getter):
            if mapper:
                return lambda event: mapper(getter(event))
            return getter

        param_handlers = []
        for name in param_names:
            getter = operator.attrgetter(name)
            mapper = param_mappers.get(name)
            param_handlers.append((name, make_getter(mapper, getter)))

        def prep_args(event):
            return {name: get(event) for name, get in param_handlers}

        def new_handler(event):
            try:
                prepped = prep_args(event)
            except ValueError:
                # If we couldn't construct the keys/mouse objects representing
                # the button that was pressed, then skip the event handler.
                #
                # This happens because Pygame can generate key codes that it
                # does not have constants for.
                return
            else:
                return handler(**prepped)

        return new_handler

    CTRL_ALT = pygame.KMOD_CTRL | pygame.KMOD_META
    SHIFT = pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT

    def dispatch_event(self, event):
        if event.type == pygame.QUIT:
            sys.exit(0)
        if event.type == pygame.KEYDOWN:
            self.keyboard._press(event.key)
            if event.key == pygame.K_q and event.mod & self.CTRL_ALT:
                sys.exit(0)
            elif event.key == pygame.K_F12:
                video = event.mod & self.SHIFT
                event = ScreenShotEvent(ScreenShotEvent, video)
        elif event.type == pygame.KEYUP:
            self.keyboard._release(event.key)

        handler = self.handlers.get(event.type)
        if handler:
            handler(event)
            return True
        return False

    def run(self):
        """Run the main loop."""
        pgzclock = wasabi2d.clock.clock

        timefunc = time.perf_counter
        sleepfunc = time.sleep
        MIN_FRAMETIME = 1 / 60  # 60fps

        t = timefunc()
        dt = 0.0
        updated = True  # Need to draw initial scene
        while True:
            for event in self.get_events():
                updated |= self.dispatch_event(event)

            updated |= pgzclock.tick(dt)

            ev = UpdateEvent(UpdateEvent, t, dt, self.keyboard)
            updated |= self.dispatch_event(ev)

            # Because the current draw strategy a single draw is
            # only flipped at the next draw. Therefore we must always issue
            # a draw event. However we pass the "updated" flag and hope the
            # renderer can deal with this.
            self.dispatch_event(DrawEvent(DrawEvent, t, dt, updated))

            # Pygame has a clock class that can do constant framerate, but it
            # only calculates time in milliseconds, which is not precise enough
            # when each frame is about 16.7ms.
            frametime = timefunc() - t
            delay = max(0, MIN_FRAMETIME - frametime)
            sleepfunc(delay)
            dt = timefunc() - t
            if self.lock_fps:
                dt = 1.0 / 60.0
            t += dt
            updated = False
