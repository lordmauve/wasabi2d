"""Wrapper around window creation."""
import numpy as np
import pygame
import pygame.image
import pygame.display
import moderngl
from pyrr import Matrix44

from .layers import LayerGroup


class Scene:
    """Top-level interface for renderable objects."""

    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height

        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK,
            pygame.GL_CONTEXT_PROFILE_CORE
        )
        self.screen = pygame.display.set_mode(
            (width, height),
            flags=pygame.OPENGL | pygame.DOUBLEBUF,
            depth=24
        )
        ctx = self.ctx = moderngl.create_context()

        self.layers = LayerGroup(ctx)

        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self.camera = Camera(width, height)

        from . import event
        event(self.draw)

        self.background = (0.0, 0.0, 0.0)

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
        pygame.image.save(img, filename)

    def draw(self, t, dt):
        assert len(self.background) == 3, \
            "Scene.background must be a 3-element tuple."
        self.ctx.clear(*self.background)
        self.layers.render(self.camera.proj, t, dt)


class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self._proj = Matrix44.orthogonal_projection(
            left=0, right=width, top=height, bottom=0, near=-1000, far=1000,
        ).astype('f4')
        self._xform = np.identity(4, dtype='f4')

    @property
    def pos(self):
        return self._xform[-1][:2]

    @pos.setter
    def pos(self, v):
        assert len(v) == 2
        self._xform[:2][-1] = v

    @property
    def proj(self):
        return self._xform @ self._proj
