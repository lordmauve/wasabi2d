"""Wrapper around window creation."""
import sys
import math
import gc
import os
from typing import Tuple, Optional, Union
from contextlib import contextmanager

import numpy as np
import pygame
import pygame.image
import pygame.transform
import pygame.display
import moderngl
from pyrr import Matrix44
from wasabigeom import vec2

from . import clock
from .layers import LayerGroup
from .loaders import set_root, images
from .color import convert_color_rgb
from .chain import LayerRange
from .shaders import bind_framebuffer, blend_func, run_shader


def capture_screen(fb: moderngl.Framebuffer) -> pygame.Surface:
    """Capture contents of the given framebuffer as a Pygame Surface."""
    width = fb.width
    height = fb.height
    data = fb.read(components=3)
    assert len(data) == (width * height * 3), \
        f"Received {len(data)}, expected {width * height * 3}"
    img = pygame.image.fromstring(data, (width, height), 'RGB')
    return pygame.transform.flip(img, False, True)


class Window:
    """Top-level interface for renderable objects.

    :param width: The width of the window to create, in pixels.
    :param height: The height of the window to create, in pixels.
    :param rootdir: The root directory to load for asset loading. Images will
                    be loaded from the ``images/`` directory inside `rootdir`,
                    for example, and corresponding directories for sounds,
                    fonts, and music.
    :param title: The initial window title.
    :param icon: The icon for the window, as an image name without extension.
    :param scaler: If True or a string, activate scene scaling using the named
                   scaler, or 'nearest' if ``True`` is given.
    :param background: An initial setting for the :py:attr:`.background`.
    :param pixel_art: If True, turn off texture filtering globally. This
                      makes pixels look square. See :ref:`pixel-art`.
    """
    def __init__(
            self,
            width: int = 800,
            height: int = 600,
            title: str = "wasabi2d",
            *,
            fullscreen: bool = False,
            icon: str = None,
            rootdir: Optional[str] = None,
            scaler: Union[str, bool, None] = False,
            pixel_art: bool = False):
        self._recording = False
        self._scaler = scaler

        if rootdir is None:
            try:
                import __main__
                rootdir = __main__.__file__
            except (KeyError, ImportError):
                import os
                rootdir = os.getcwd()
        set_root(rootdir)

        pygame.init()
        self.drawer = Drawer()
        self.width = width
        self.height = height
        self.fullscreen = fullscreen

        if icon:
            icon_img = images.load(icon)
        else:
            import io
            import pkgutil
            icon_data = pkgutil.get_data(__name__, 'data/icon.png')
            icon_img = pygame.image.load(io.BytesIO(icon_data))
        pygame.display.set_icon(icon_img)

        ctx = self.ctx = self._make_context(width, height)
        ctx.extra = {}
        ctx.extra['texture_filter'] = (
            (moderngl.NEAREST_MIPMAP_NEAREST, moderngl.NEAREST)
            if pixel_art else
            (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        )

        self.title = title

        ctx.enable(moderngl.BLEND)
        self.ctx.extra['blend_func'] = self.ctx.blend_func = (
            moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA,
            moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA,
        )

        from . import event
        event(self.draw)
        event(self.on_screenshot_requested)
        self.viewports = []
        self._dirty = False

    @property
    def dims(self) -> vec2:
        """Get the size of the window."""
        return vec2(self.width, self.height)

    def release(self):
        self.layers.clear()
        if self.ctx:
            self.drawer = None
            self.ctx.extra.pop('shadermgr').release()
            self.ctx.release()
            self.ctx = None
            for vp in self.viewports:
                vp.delete()
            self.viewports.clear()
        gc.collect()

    def __del__(self):
        self.release()

    def _make_context(self, width, height):
        """Create the ModernGL context."""
        glconfig = {
            'GL_CONTEXT_MAJOR_VERSION': 4,
            'GL_CONTEXT_PROFILE_MASK': pygame.GL_CONTEXT_PROFILE_CORE,
        }

        for k, v in glconfig.items():
            k = getattr(pygame, k)
            pygame.display.gl_set_attribute(k, v)

        dims = width, height
        flags = pygame.OPENGL | pygame.DOUBLEBUF

        if self.fullscreen:
            # SDL's detection for "legacy" fullscreen seems to fail on
            # Ubuntu 16.04 at least. Set an environment variable so that it
            # asks the Window Manager for full screen mode instead.
            # https://github.com/spurious/SDL-mirror/blob/c8b01e282dfd49ea8bbf1faec7fd65d869ea547f/src/video/x11/SDL_x11window.c#L1468
            os.environ['SDL_VIDEO_X11_LEGACY_FULLSCREEN'] = "0"

            flags |= pygame.FULLSCREEN
            if not self._scaler:
                self._scaler = 'linear'
            dims = 0, 0
        elif self._scaler:
            flags |= pygame.SCALED

        pygame.display.set_mode(
            dims,
            flags=flags,
            depth=24,
            vsync=True
        )
        ctx = moderngl.create_context(require=410)

        self._real_size = pygame.display.get_window_size()
        if self._real_size != (width, height):
            self.drawer = self._make_scaler(ctx, (width, height))
        return ctx

    def _make_scaler(self, ctx, dims):
        """Get a scaler instance."""
        cls = {
            True: NearestScaler,
            'nearest': NearestScaler,
            'linear': LinearScaler,
        }[self._scaler]
        return cls(ctx, dims)

    @property
    def title(self):
        """Get the window title."""
        return self._title

    @title.setter
    def title(self, title):
        """Set the window title."""
        self._title = title
        pygame.display.set_caption(title)

    def on_screenshot_requested(self, video):
        """Handle a screenshot event from the event sytem."""
        if video:
            self.toggle_recording()
        else:
            self.screenshot()

    def screenshot(self, filename: Optional[str] = None) -> str:
        """Take a screenshot.

        If filename is not given, save to a file named screenshot_<time>.png
        in the current directory. Return the filename.

        """
        import datetime
        if filename is None:
            now = datetime.datetime.now()
            filename = f'screenshot_{now:%Y-%m-%d_%H:%M:%S.%f}.png'
        img = capture_screen(self.ctx.screen)
        pygame.image.save(img, filename)
        print(f"Wrote screenshot to {filename}")
        return filename

    def record_video(self, filename=None):
        """Start recording a video.

        Video will be encoded in MPEG4 format.

        This requires an ffmpeg binary to be located on $PATH.

        If filename is not given, save to a file named video_<time>.mp4
        in the current directory.
        """
        import subprocess
        import datetime
        if not filename:
            now = datetime.datetime.now()
            filename = f'video_{now:%Y-%m-%d_%H:%M:%S.%f}.mp4'
        self._recording = filename
        w, h = self._real_size
        command = [
            'ffmpeg',
            '-y',  # (optional) overwrite output file if it exists
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{w}x{h}',  # size of one frame
            '-pix_fmt', 'rgb24',
            '-r', '60',  # frames per second
            '-i', '-',  # The imput comes from a pipe
            '-vf', 'vflip',

            # These options are needed for uploads to Twitter
            '-vcodec', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-strict', '-2',
            '-an',  # Tells FFMPEG not to expect any audio
            filename,
        ]
        self._ffmpeg = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            bufsize=0
        )
        print("Recording video...")
        from . import loop
        loop.lock_fps = True
        self.vid_thread = None

    def stop_recording(self):
        """Finish recording the current video."""
        if self.vid_thread:
            self.vid_thread.join()
        self._ffmpeg.stdin.close()
        ret = self._ffmpeg.wait()
        if ret == 0:
            print("Saved recording to", self._recording)
        else:
            print("Error writing video.")
        self._recording = None
        from . import loop
        loop.lock_fps = False

    def toggle_recording(self) -> bool:
        """Start or stop recording video.

        Return True if recording started.
        """
        if not self._recording:
            self.record_video()
            return True
        else:
            self.stop_recording()

    def _vid_frame(self):
        data = self.ctx.screen.read(components=3)
        self._ffmpeg.stdin.write(data)

    _fps_query = None
    fps = 60
    unflipped = False

    def draw(self, t, dt, updated):
        if self._fps_query:
            self._fps_query.__exit__(None, None, None)
            self.fps = 1e9 / (self._fps_query.elapsed or 1e9)

        if self._recording:
            self._vid_frame()

        if self.unflipped:
            self._flip()

        if updated:
            self._fps_query = self.ctx.query(time=True)
            self._fps_query.__enter__()
            self.drawer.draw(self)
            self.unflipped = True
        else:
            self._fps_query = None
            self.unflipped = False

    _flip = staticmethod(pygame.display.flip)

    def create_viewport(
            self,
            width=None,
            height=None,
            x=0,
            y=0,
            background=None,
        ) -> 'Viewport':
        """Create a viewport"""
        vp = Viewport(self, width or self.width, height or self.height, x, y)
        self.viewports.append(vp)
        vp.background = background
        return vp


class Scene(Window):
    """A shortcut to build a window with a single viewport."""

    def __init__(
            self,
            *args,
            background: Union[str, Tuple[float, float, float]] = 'black',
            **kwargs
        ):
        super().__init__(*args, **kwargs)
        vp = self.viewport = self.create_viewport()
        self.background = background
        self.camera = vp.camera
        self.layers = vp.layers

    @property
    def chain(self):
        """Expose the viewport's chain as a scene attribute."""
        return self.viewport.chain

    @chain.setter
    def chain(self, v):
        """Set the viewport's chain."""
        self.viewport.chain = v

    @property
    def background(self) -> Tuple[float, float, float]:
        """Get the background colour for the whole scene."""
        return self.viewport.background

    @background.setter
    def background(self, v):
        """Set the background colour for the whole scene."""
        self.viewport.background = v


class Viewport:
    __slots__ = (
        'window',
        '_width',
        '_height',
        '_x',
        '_y',
        'chain',
        'camera',
        'layers',
        '_background',
    )

    def __init__(self, window, width, height, x=0, y=0):
        self.window = window
        self._width = round(width)
        self._height = round(height)
        self._x = round(x)
        self._y = round(y)

        # Default chain: render all layers
        self.chain = [LayerRange()]

        self.camera = Camera(window.ctx, self._width, self._height)
        self.layers = LayerGroup(window.ctx)
        self._background = None

    @property
    def background(self) -> Tuple[float, float, float]:
        """Get the background colour for the whole scene."""
        return self._background

    @background.setter
    def background(self, v):
        """Set the background colour for the whole scene."""
        if v is None:
            self._background = None
        else:
            self._background = convert_color_rgb(v)

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, v):
        self.window._dirty = True
        self._x = round(v)

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, v):
        self.window._dirty = True
        self._y = round(v)

    @property
    def center(self):
        return vec2(self.x, self.y) + 0.5 * self.dims

    @center.setter
    def center(self, v):
        x, y = vec2(*v) - 0.5 * self.dims
        self.x = x
        self.y = y

    @property
    def dims(self):
        return vec2(self._width, self._height)

    @dims.setter
    def dims(self, v):
        w, h = v
        w = round(w)
        h = round(h)
        assert w > 0, f"Cannot set viewport width to {w}"
        assert h > 0, f"Cannot set viewport height to {h}"
        self._width = round(w)
        self._height = round(h)
        self.window._dirty = True
        self.camera.resize(self._width, self._height)

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, v):
        v = round(v)
        assert v > 0, f"Cannot set viewport width to {v}"
        self.window._dirty = True
        self._width = v
        self.camera.resize(self._width, self._height)

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, v):
        v = round(v)
        assert v > 0, f"Cannot set viewport height to {v}"
        self.window._dirty = True
        self._height = v
        self.camera.resize(self._width, self._height)

    @property
    def _rect(self):
        return (self._x, self._y, self._width, self._height)

    @property
    def rect(self):
        return pygame.Rect(*self._rect)

    def draw(self):
        ctx = self.window.ctx
        prev_vp = ctx.viewport
        ctx.viewport = self._rect
        try:
            if self.background is not None:
                ctx.clear(*self._background, viewport=self._rect)
            self.layers._update(self.camera.proj)
            for op in self.chain:
                op.draw(self)
        finally:
            ctx.viewport = prev_vp

    def delete(self):
        self.window.viewports.remove(self)
        self.camera.release()

    def clone(self, width=None, height=None, x=None, y=None) -> 'Viewport':
        """Create a new Viewport that shares the scene with this one.

        The new viewport will have its own dimensions and an independent camera
        object.
        """
        vp = Viewport.__new__(Viewport)
        self.window.viewports.append(vp)
        vp.window = self.window
        vp._width = self.width if width is None else width
        vp._height = self.height if height is None else height
        vp._x = self.x if x is None else x
        vp._y = self.y if y is None else y
        vp._background = self._background

        vp.chain = self.chain
        vp.camera = Camera(self.window.ctx, vp.width, vp.height)
        vp.layers = self.layers
        vp._background = self.background

        return vp


class Drawer:
    """Render the scene using the chain."""
    def draw(self, window):
        if window._dirty:
            window.ctx.clear()
            window._dirty = False
        for vp in window.viewports:
            vp.draw()


class NearestScaler(Drawer):
    """Render the scene using the chain, but scaled."""
    def __init__(self, ctx, logical_size):
        self.ctx = ctx
        self.tex = ctx.texture(
            logical_size,
            3,
            dtype='f1',
        )
        self.tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self._fb = ctx.framebuffer(color_attachments=[self.tex])

    def __del__(self):
        self._fb.release()
        self.tex.release()

    def draw(self, window):
        with bind_framebuffer(self.ctx, self._fb, clear=True):
            super().draw(window)
        with blend_func(self.ctx, moderngl.ONE, moderngl.ZERO):
            run_shader(
                self.ctx,
                """\
#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D image;

void main()
{
    f_color = texture(image, uv);
}
""",
                image=self.tex,
            )


class LinearScaler(NearestScaler):
    """Render and upscale the scene using linear interpolation."""

    def __init__(self, ctx, logical_size):
        super().__init__(ctx, logical_size)
        self.tex.filter = (moderngl.LINEAR, moderngl.LINEAR)


class HeadlessScene(Scene):
    """A scene that doesn't create a window.

    This can be used in automated applications and for testing.

    """
    def __init__(
            self,
            width: int = 800,
            height: int = 600,
            rootdir: Optional[str] = None):
        super().__init__(width=width, height=height, rootdir=rootdir)

    def _make_context(self, width, height):
        ctx = moderngl.create_standalone_context(require=410)
        screen = ctx._screen = ctx.simple_framebuffer(
            (width, height),
        )
        screen.use()
        return ctx

    def _flip(self):
        """Flipping is a no-op."""


class Camera:
    """The camera/viewport through which the scene is viewed.

    As well as constructing a projection matrix for the screen, and offering
    some dynamic effects such as screen shake, a Camera serves as a manager
    for temporary framebuffers corresponding to the viewport size.
    """

    def __init__(self, ctx, width, height):
        self.ctx = ctx
        self._xform = np.identity(4, dtype='f4')
        self._cam_offset = np.zeros(2, dtype='f4')
        self._cam_vel = np.zeros(2, dtype='f4')
        self._pos = np.zeros(2, dtype='f4')
        self._fbs = {}
        self.resize(width, height)
        self.pos = vec2(self.width, self.height) * 0.5

    def resize(self, width, height):
        self.release()  # release framebuffers allocated for the old size
        self.width = width
        self.height = height
        self.dims = (width, height)
        hw = self.width * 0.5
        hh = self.height * 0.5
        self._proj = Matrix44.orthogonal_projection(
            left=-hw,
            right=hw,
            top=hh,
            bottom=-hh,
            near=-1000,
            far=1000
        ).astype('f4')

    @contextmanager
    def temporary_fbs(self, num=1, dtype='f1', samples=0):
        """Reserve temporary framebuffer objects of the given dtype.

        It is recommended to use the single-framebuffer version instead of
        this one; this one encourages reserving framebuffers that you are not
        yet ready to use, which can result in over-allocation.

        The reservation is released when the context exits.

        For example::

            with camera.temporary_fbs(2, 'f2') as (fb1, fb2):
                ... do something clever ...

            # fb1 and fb2 are now returned to the pool; do not use them

        """
        temps = self._fbs.setdefault((dtype, samples), [])

        reserved = temps[-num:]
        del temps[-num:]

        while len(reserved) < num:
            fb = self._make_fb(dtype, samples=samples)
            reserved.append(fb)

        try:
            yield reserved
        finally:
            temps.extend(reserved)

    @contextmanager
    def temporary_fb(self, dtype='f1', samples=0):
        """Reserve a temporary framebuffer of the given type.

        The reservation is released when the context exits.

        For example:

            with camera.temporary_fb() as fb:
                with bind_framebuffer(ctx, fb, clear=True):
                    ... do something clever ...
                # Use textures attached to fb

        """
        with self.temporary_fbs(1, dtype, samples) as (fb,):
            yield fb

    def bind_framebuffer(self, fb, clear=True):
        """Bind a framebuffer during the context."""
        return bind_framebuffer(self.ctx, fb, clear=clear)

    def _make_fb(self, dtype='f1', div_x=1, div_y=1, samples=0):
        """Make a new framebuffer corresponding to this viewport."""
        tex = self.ctx.texture(
            (self.width // div_x, self.height // div_y),
            4,
            dtype=dtype,
            samples=samples
        )
        tex.repeat_x = tex.repeat_y = False
        return self.ctx.framebuffer([tex])

    def __del__(self):
        self.release()

    def release(self):
        for fbs in self._fbs.values():
            for fb in fbs:
                fb.release()
        self._fbs.clear()

    def run_shader(self, fragment_shader: str, **uniforms):
        """Execute a fragment shader over the viewport.

        The program and buffers will be cached and re-used.

        Uniforms may be given as keyword arguments. Be sure to specify all
        uniforms, as reusing a program will mean that previously set values
        will be used.

        """
        run_shader(self.ctx, fragment_shader, **uniforms)

    @property
    def zoom(self):
        return self._xform[0, 0]

    @zoom.setter
    def zoom(self, zoom):
        self._xform[0, 0] = self._xform[1, 1] = zoom

    @property
    def pos(self):
        return vec2(*self._pos)

    @pos.setter
    def pos(self, v):
        self._pos[:] = vec2(v)
        self._xform[-1, :2] = self._cam_offset - self._pos

    @property
    def proj(self):
        return self._xform @ self._proj

    def _getproj(self, parallax=1.0):
        if parallax == 1.0:
            return self._xform @ self._proj
        pos = tuple(self._xform[-1, :2])
        self._xform[-1, :2] *= parallax
        p = self._xform @ self._proj
        self._xform[-1, :2] = pos
        return p

    def screen_shake(self, dist=25):
        """Trigger a screen shake effect.

        The camera will be offset from ``.pos`` by ``dist`` in a random
        direction; then steady itself in a damped harmonic motion.

        """
        theta = np.random.uniform(0, math.tau)
        basis = np.array([theta, + math.pi * 0.5])
        self._cam_offset[:] = dist * np.sin(basis)
        self._xform[-1][:2] = self._cam_offset - self._pos
        clock.schedule_unique(self._steady_cam, 0.01)

    def _steady_cam(self):
        dt = 0.05  # guarantee stable behaviour
        self._cam_offset += self._cam_vel * dt
        self._cam_vel -= self._cam_offset * (300 * dt)
        self._cam_vel *= 0.1 ** dt
        self._cam_offset *= 0.01 ** dt
        if np.sum(self._cam_vel ** 2) < 1e-3 \
                and np.sum(self._cam_offset ** 2) < 1e-2:
            self._cam_offset[:] = self._cam_vel[:] = 0
        else:
            clock.schedule_unique(self._steady_cam, 0.01)
        self._xform[-1][:2] = self._cam_offset - self._pos
