"""Base functionality for post-processing effects."""
import numpy as np
import moderngl


POSTPROCESS_VERT_PROGRAM = '''
    #version 330

    in vec2 in_vert;
    in vec2 in_uv;
    out vec2 uv;

    void main() {
        gl_Position = vec4(in_vert.xy, 0.0, 1.0);
        uv = in_uv;
    }
'''


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
            shadermgr: 'wasabi2d.layers.ShaderManager',
            fragment_shader: str,
            send_uvs: bool = True):
        self.ctx = ctx
        self.prog = shadermgr.get(
            vertex_shader=POSTPROCESS_VERT_PROGRAM,
            fragment_shader=fragment_shader,
        )

        indices = ctx.buffer(self.QUAD_INDICES)
        vs_uvs = ctx.buffer(self.QUAD_VERTS_UVS)

        if send_uvs:
            attribs = (vs_uvs, '2f4 2f4', 'in_vert', 'in_uv')
        else:
            attribs = (vs_uvs, '2f4 8x', 'in_vert')
        self.vao = ctx.vertex_array(
            self.prog,
            [attribs],
            index_buffer=indices
        )

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

            self.prog[k].value = v
        self.vao.render(moderngl.TRIANGLES, 6)

