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


DrawEvent = namedtuple('DrawEvent', 'type t dt')
UpdateEvent = namedtuple('UpdateEvent', 'type t dt keyboard')


class EventMapper:
    def __init__(self):
        self.keyboard = wasabi2d.keyboard.keyboard
        self.handlers = {}
        self.lock_fps = False

    EVENT_HANDLERS = {
        'on_mouse_down': pygame.MOUSEBUTTONDOWN,
        'on_mouse_up': pygame.MOUSEBUTTONUP,
        'on_mouse_move': pygame.MOUSEMOTION,
        'on_key_down': pygame.KEYDOWN,
        'on_key_up': pygame.KEYUP,
        'on_music_end': constants.MUSIC_END,
        'draw': DrawEvent,
        'update': UpdateEvent,
    }

    def map_buttons(val):
        return {c for c, pressed in zip(constants.mouse, val) if pressed}

    EVENT_PARAM_MAPPERS = {
        'buttons': map_buttons,
        'button': constants.mouse,
        'key': constants.keys
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
        self.handlers[type] = self.prepare_handler(handler)
        return handler

    def prepare_handler(self, handler):
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
            mapper = self.EVENT_PARAM_MAPPERS.get(name)
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

    def dispatch_event(self, event):
        if event.type == pygame.QUIT:
            sys.exit(0)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q and \
                    event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META):
                sys.exit(0)
            self.keyboard._press(event.key)
        elif event.type == pygame.KEYUP:
            self.keyboard._release(event.key)

        handler = self.handlers.get(event.type)
        if handler:
            self.need_redraw = True
            handler(event)
            return True
        return False

    def run(self):
        """Run the main loop."""
        clock = pygame.time.Clock()
        # self.reinit_screen()

        pgzclock = wasabi2d.clock.clock

        self.need_redraw = True
        t = 0
        while True:
            dt = clock.tick(60) / 1000.0

            if self.lock_fps:
                dt = 1.0 / 60.0

            t += dt

            for event in pygame.event.get():
                self.dispatch_event(event)

            pgzclock.tick(dt)

            ev = UpdateEvent(UpdateEvent, t, dt, self.keyboard)
            updated = self.dispatch_event(ev)

            screen_change = False  # self.reinit_screen()
            if screen_change or updated or pgzclock.fired or self.need_redraw:
                self.dispatch_event(DrawEvent(DrawEvent, t, dt))
                pygame.display.flip()
                self.need_redraw = False
