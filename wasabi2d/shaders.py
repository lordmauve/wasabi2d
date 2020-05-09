"""Manage the compilation of programs in a context."""
from typing import Optional, Dict, Tuple
from contextlib import contextmanager
import pkgutil

import moderngl
import numpy as np


class ShaderManager:
    """Cache of compiled programs for a context.

    The shadermanager is cached onto the context object.

    """
    ctx: moderngl.Context
    files: Dict[str, str]
    programs: Dict[Tuple[str, str, Optional[str]], moderngl.Program]

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        if not ctx.extra:
            ctx.extra = {}
        if 'shadermgr' in ctx.extra:
            raise ValueError(f"ShaderManager is already defined for {ctx}")
        ctx.extra['shadermgr'] = self
        self.files = {}
        self.programs = {}

    def _read(self, name: str):
        """Read a GLSL file from the wasabi2d directory."""
        return pkgutil.get_data('wasabi2d', 'glsl/' + name).decode('utf-8')

    def load(self, *names) -> moderngl.Program:
        """Load a program from the wasabi2d/glsl directory.

        If a single argument is given, load shaders from files with a common
        name, and use a geometry shader if it exists.

        Also accepts two or three arguments to specify separate filenames for
        each shader stage. Stages are in vert, geom, frag order and the geom
        stage is optional.

        """
        if names in self.programs:
            return self.programs[names]

        if len(names) == 1:
            name = names[0]
            try:
                geom_shader = self._read(f'{name}.geom')
            except FileNotFoundError:
                geom_shader = None
            prog = self.programs[names] = self.ctx.program(
                vertex_shader=self._read(f'{name}.vert'),
                geometry_shader=geom_shader,
                fragment_shader=self._read(f'{name}.frag'),
            )
        elif len(names) == 2:
            vert, frag = names
            prog = self.programs[names] = self.ctx.program(
                vertex_shader=self._read(f'{vert}.vert'),
                fragment_shader=self._read(f'{frag}.frag'),
            )
        elif len(names) == 3:
            vert, geom, frag = names
            prog = self.programs[names] = self.ctx.program(
                vertex_shader=self._read(f'{vert}.vert'),
                geometry_shader=self._read(f'{geom}.geom'),
                fragment_shader=self._read(f'{frag}.frag'),
            )
        else:
            raise ValueError("Unexpected number of files.")
        return prog

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
        projmatrix = proj.tobytes()
        for prog in self.programs.values():
            try:
                uniform = prog['proj']
            except KeyError:
                continue
            uniform.write(projmatrix)

    def __del__(self):
        self.release()

    def release(self):
        for prog in self.programs.values():
            prog.release()
        self.programs.clear()


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
            fb.clear(0, 0, 0, 0)
        yield
    finally:
        orig_screen.use()
        ctx._screen = orig_screen


blend_aliases = {
    '1': moderngl.ONE,
    1: moderngl.ONE,
    '0': moderngl.ZERO,
    0: moderngl.ZERO,
    'a': moderngl.SRC_ALPHA,
    'da': moderngl.DST_ALPHA,
    '1-a': moderngl.ONE_MINUS_SRC_ALPHA,
    '1-da': moderngl.ONE_MINUS_DST_ALPHA,
}


@contextmanager
def blend_func(
    ctx,
    src=moderngl.SRC_ALPHA,
    dest=moderngl.ONE_MINUS_SRC_ALPHA,
    src_a=moderngl.ONE,
    dest_a=moderngl.ONE_MINUS_SRC_ALPHA,
):
    """Override the blending function for the duration of the context."""
    src = blend_aliases.get(src, src)
    dest = blend_aliases.get(dest, dest)
    src_a = blend_aliases.get(src_a, src_a)
    dest_a = blend_aliases.get(dest_a, dest_a)

    ctx.blend_func = src, dest, src_a, dest_a
    try:
        yield
    finally:
        ctx.blend_func = (
            moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA,
            moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA
        )
