"""Manage the compilation of programs in a context."""
from typing import Optional, Dict, Tuple
from contextlib import contextmanager

import moderngl
import numpy as np


class ShaderManager:
    """Cache of compiled programs for a context.

    The shadermanager is cached onto the context object.

    """
    ctx: moderngl.Context
    programs: Dict[Tuple[str, str, Optional[str]], moderngl.Program]

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        if not ctx.extra:
            ctx.extra = {}
        if 'shadermgr' in ctx.extra:
            raise ValueError(f"ShaderManager is already defined for {ctx}")
        ctx.extra['shadermgr'] = self
        self.programs = {}

    def get(
        self,
        vertex_shader: str,
        fragment_shader: str,
        geometry_shader: Optional[str] = None
    ) -> moderngl.Program:
        """Get a compiled program."""
        assert isinstance(vertex_shader, str)
        assert isinstance(fragment_shader, str)
        assert isinstance(geometry_shader, (str, type(None)))
        k = vertex_shader, fragment_shader, geometry_shader
        try:
            return self.programs[k]
        except KeyError:
            pass

        prog = self.programs[k] = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
            geometry_shader=geometry_shader,
        )
        return prog

    def set_proj(self, proj: np.ndarray):
        """Set the projection matrix."""
        for prog in self.programs.values():
            try:
                uniform = prog['proj']
            except KeyError:
                continue
            uniform.write(proj.tobytes())


def shadermgr(ctx: moderngl.Context) -> ShaderManager:
    """Shortcut to get or create the shader manager for a context."""
    return ctx.extra['shadermgr']


@contextmanager
def bind_framebuffer(ctx, fb, *, clear=False):
    """Bind an alternative framebuffer during a context.

    The previous binding will be restored when the context exits.

    If `clear` is True, also clear the framebuffer.

    """
    orig_screen = ctx._screen
    ctx._screen = fb
    try:
        fb.use()
        if clear:
            ctx.clear()
        yield
    finally:
        orig_screen.use()
        ctx._screen = orig_screen


@contextmanager
def blend_func(ctx, src=moderngl.SRC_ALPHA, dest=moderngl.ONE_MINUS_SRC_ALPHA):
    """Override the blending function for the duration of the context."""
    ctx.blend_func = src, dest
    try:
        yield
    finally:
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
