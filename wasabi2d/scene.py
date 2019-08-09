"""Wrapper around window creation."""
import numpy as np
import pygame
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

        layers = self.layers = LayerGroup(ctx)

        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self.camera = Camera(width, height)

        from . import event
        @event
        def draw(t, dt):
            layers.render(self.camera.proj, t, dt)


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
