"""Wrapper around window creation."""
import math
import numpy as np
import pygame
import pygame.image
import pygame.transform
import pygame.display
import moderngl
from pyrr import Matrix44

from . import clock
from .layers import LayerGroup


class Scene:
    """Top-level interface for renderable objects."""

    def __init__(
            self,
            width=800,
            height=600,
            antialias=0,
            title="wasabi2d"):
        self.width = width
        self.height = height

        self._recording = False

        pygame.init()

        glconfig = {
            'GL_CONTEXT_MAJOR_VERSION': 4,
            'GL_CONTEXT_MINOR_VERSION': 3,
            'GL_CONTEXT_PROFILE_MASK': pygame.GL_CONTEXT_PROFILE_CORE,
        }

        if antialias:
            glconfig.update({
                'GL_MULTISAMPLEBUFFERS': 1,
                'GL_MULTISAMPLESAMPLES': antialias,
            })

        for k, v in glconfig.items():
            k = getattr(pygame, k)
            pygame.display.gl_set_attribute(k, v)

        self.screen = pygame.display.set_mode(
            (width, height),
            flags=pygame.OPENGL | pygame.DOUBLEBUF,
            depth=24
        )
        self.title = title
        ctx = self.ctx = moderngl.create_context()

        self.layers = LayerGroup(ctx)

        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self.camera = Camera(width, height)

        from . import event
        event(self.draw)

        self.background = (0.0, 0.0, 0.0)

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, title):
        self._title = title
        pygame.display.set_caption(title)

    def screenshot(self, filename=None):
        """Take a screenshot."""
        import datetime
        if filename is None:
            now = datetime.datetime.now()
            filename = f'screenshot_{now:%Y-%m-%d_%H:%M:%S.%f}.png'
        data = self.ctx.screen.read(components=3)
        assert len(data) == (self.width * self.height * 3), \
            f"Received {len(data)}, expected {self.width * self.height * 3}"
        img = pygame.image.fromstring(data, (self.width, self.height), 'RGB')
        img = pygame.transform.flip(img, False, True)
        pygame.image.save(img, filename)

    def record_video(self, filename=None):
        """Start recording a video.

        This requires an ffmpeg binary to be located on $PATH.
        """
        import subprocess
        import datetime
        if not filename:
            now = datetime.datetime.now()
            filename = f'video_{now:%Y-%m-%d_%H:%M:%S.%f}.mp4'
        self._recording = filename
        command = [
            'ffmpeg',
            '-y',  # (optional) overwrite output file if it exists
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{self.width}x{self.height}',  # size of one frame
            '-pix_fmt', 'rgb24',
            '-r', '60',  # frames per second
            '-i', '-',  # The imput comes from a pipe
            '-vf', 'vflip',
            '-an',  # Tells FFMPEG not to expect any audio
            filename,
        ]
        self._ffmpeg = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            bufsize=10**8
        )
        print("Recording video...")

    def stop_recording(self):
        """Stop recording videos."""
        self._ffmpeg.stdin.close()
        ret = self._ffmpeg.wait()
        if ret == 0:
            print("Saved recording to", self._recording)
        else:
            print("Error writing video.")
        self._recording = None

    def toggle_recording(self) -> bool:
        """Start or stop recording.

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
        self._ffmpeg.stdin.flush()

    def draw(self, t, dt):
        assert len(self.background) == 3, \
            "Scene.background must be a 3-element tuple."
        self.ctx.clear(*self.background)
        self.layers.render(self.camera.proj, t, dt)
        if self._recording:
            self._vid_frame()


class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
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
        self._xform = np.identity(4, dtype='f4')
        self._cam_offset = np.zeros(2, dtype='f4')
        self._cam_vel = np.zeros(2, dtype='f4')
        self._pos = np.zeros(2, dtype='f4')
        self.pos = hw, hh

    @property
    def pos(self):
        return -self._xform[-1][:2]

    @pos.setter
    def pos(self, v):
        assert len(v) == 2
        self._pos[:] = v
        self._xform[-1][:2] = self._cam_offset - self._pos

    @property
    def proj(self):
        return self._xform @ self._proj

    def screen_shake(self, dist=25):
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

