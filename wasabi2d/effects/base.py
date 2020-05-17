"""Base functionality for post-processing effects."""
import numpy as np
import moderngl

from ..shaders import shadermgr


class PostprocessPass:
    """A full-screen postprocessing effect pass.

    This will render a full-screen quad using a single fragment shader.

    """
    # TODO: let the shadermanager itself manage these, so that they
    # are shared between layers etc

    QUAD_INDICES = np.array([0, 1, 2, 0, 2, 3], dtype='i4')
    QUAD_VERTS_UVS = np.array([
        [-1, -1, 0, 0],
        [1, -1, 1, 0],
        [1, 1, 1, 1],
        [-1, 1, 0, 1],
    ], dtype='f4')

    def __init__(
            self,
            ctx: moderngl.Context,
            shader_name: str=None,
            text: str=None,
            send_uvs: bool = True):
        self.ctx = ctx
        if shader_name:
            self.prog = shadermgr(ctx).load(
                'postprocess/postprocess',
                shader_name
            )
        else:
            sm = shadermgr(ctx)
            self.prog = sm.get(
                sm._read('postprocess/postprocess.vert'),
                text
            )

        self.indices = ctx.buffer(self.QUAD_INDICES)
        self.vs_uvs = ctx.buffer(self.QUAD_VERTS_UVS)

        if send_uvs:
            attribs = (self.vs_uvs, '2f4 2f4', 'in_vert', 'in_uv')
        else:
            attribs = (self.vs_uvs, '2f4 8x', 'in_vert')
        self.vao = ctx.vertex_array(
            self.prog,
            [attribs],
            index_buffer=self.indices
        )

    def __del__(self):
        self.vao.release()
        self.indices.release()
        self.vs_uvs.release()

    def set_region(self, xfrac=1, yfrac=1):
        """Set the pass to write to a subregion of the viewport."""
        coords = self.QUAD_VERTS_UVS.copy()
        coords[:, 0] *= xfrac
        coords[:, 0] -= (1.0 - xfrac)
        coords[:, 1] *= yfrac
        coords[:, 1] -= (1.0 - yfrac)
        coords[:, 2] *= xfrac
        coords[:, 3] *= yfrac
        self.vs_uvs.write(coords)

    def render(self, **uniforms):
        """Assign the given uniforms and then render."""
        texnum = 0
        for k, v in uniforms.items():
            if isinstance(v, moderngl.Framebuffer):
                v = v.color_attachments[0]

            if isinstance(v, moderngl.Texture):
                v.use(texnum)
                v = texnum
                texnum += 1

            if isinstance(v, np.ndarray):
                self.prog[k].write(v)
            else:
                self.prog[k].value = v
        self.vao.render(moderngl.TRIANGLES, 6)
