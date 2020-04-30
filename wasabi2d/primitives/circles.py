import math
from functools import partial

import numpy as np
import moderngl

from ..color import convert_color
from ..allocators.vertlists import VAO
from .polygons import AbstractShape
from ..rect import ZRect
from ..descriptors import CallbackProp
from ..effects.base import PostprocessPass
from ..shaders import bind_framebuffer, blend_func

#: Shader for a plain color fill
PLAIN_COLOR = dict(
    vertex_shader='''
        #version 330

        uniform mat4 proj;

        in vec2 in_vert;
        in vec4 in_color;
        out vec4 color;

        void main() {
            gl_Position = proj * vec4(in_vert, 0.0, 1.0);
            color = in_color;
        }
    ''',
    fragment_shader='''
        #version 330

        out vec4 f_color;
        in vec4 color;

        void main() {
            f_color = color;
        }
    ''',
)


WIDE_LINE = dict(
    vertex_shader='''
        #version 330

        in vec2 in_vert;
        in vec4 in_color;
        in float in_linewidth;
        out vec4 g_color;
        out float widths;

        void main() {
            gl_Position = vec4(in_vert, 0.0, 1.0);
            g_color = in_color;
            widths = in_linewidth;
        }
    ''',
    geometry_shader="""
#version 330 core
layout (lines_adjacency) in;
//layout (triangle_strip, max_vertices = 2) out;
layout (triangle_strip, max_vertices = 4) out;

in vec4 g_color[];
in float widths[];
out vec4 color;

const float MITRE_LIMIT = 6.0;

vec2 rot90(vec2 v) {
    return vec2(-v.y, v.x);
}

bool is_nonzero(vec2 v) {
    return dot(v, v) > 1e-4;
}

uniform mat4 proj;


void mitre(vec2 a, vec2 b, vec2 c, float width) {
    vec2 ab = normalize(b - a);
    vec2 bc = normalize(c - b);

    if (!is_nonzero(ab)) {
        ab = bc;
    }
    if (!is_nonzero(bc)) {
        bc = ab;
    }

    // across bc
    vec2 xbc = rot90(bc);

    vec2 along = normalize(ab + bc);
    vec2 across_mitre = rot90(along);

    float scale = 1.0 / dot(xbc, across_mitre);

    //This kind of works Ok although it does cause the width to change
    // scale = min(scale, MITRE_LIMIT);  // limit extension of the mitre
    vec2 across = width * across_mitre * scale;

    gl_Position = proj * vec4(b + across, 0.0, 1.0);
    EmitVertex();

    gl_Position = proj * vec4(b - across, 0.0, 1.0);
    EmitVertex();
}


void main() {
    color = g_color[1];

    vec2 a = gl_in[0].gl_Position.xy;
    vec2 b = gl_in[1].gl_Position.xy;
    vec2 c = gl_in[2].gl_Position.xy;
    vec2 d = gl_in[3].gl_Position.xy;

    vec2 along = c - b;

    if (is_nonzero(b - a)) {
        mitre(a, b, c, widths[1]);
    } else {
        mitre(b - along, b, c, widths[1]);
    }
    if (is_nonzero(d - c)) {
        mitre(b, c, d, widths[2]);
    } else {
        mitre(b, c, c + along, widths[2]);
    }

    EndPrimitive();
}
""",
    fragment_shader='''
        #version 330

        out vec4 f_color;
        in vec4 color;

        void main() {
            f_color = color;
        }
    ''',
)


class PolyVAO(VAO):
    """VAO object that renders with multisampling."""

    #: Fragment program to copy from multisample texture
    BLEND_PROGRAM = """
    #version 330 core

    in vec2 uv;
    out vec4 f_color;
    uniform sampler2DMS image;

    uniform int samples = 4;

    void main()
    {
        vec4 color = vec4(0, 0, 0, 0);

        ivec2 pos = ivec2(uv * textureSize(image));

        for (int i = 0; i < samples; i++) {
            color += texelFetch(image, pos, i);
        }
        if (color.a == 0.0) {
            discard;
        }
        f_color = vec4(
            color.rgb / color.a,
            color.a / samples
        );
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.composite_prog = PostprocessPass(self.ctx, self.BLEND_PROGRAM)

    def render(self, camera):
        samples = min(self.ctx.max_samples, 4)
        with camera.temporary_fb(samples=samples) as fb:
            with bind_framebuffer(self.ctx, fb, clear=True):
                super().render(camera)
            self.composite_prog.render(image=fb, samples=samples)


def color_vao(
        mode: int,
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a BAO for rendering plain colored objects."""
    return PolyVAO(
        mode=mode,
        ctx=ctx,
        prog=shadermgr.get(**PLAIN_COLOR),
        dtype=np.dtype([
            ('in_vert', '2f4'),
            ('in_color', '4f4'),
        ])
    )


def line_vao(
        ctx: moderngl.Context,
        shadermgr: 'wasabi2d.layers.ShaderManager') -> VAO:
    """Build a VAO for rendering lines."""
    return PolyVAO(
        mode=moderngl.LINE_STRIP_ADJACENCY,
        ctx=ctx,
        prog=shadermgr.get(**WIDE_LINE),
        dtype=np.dtype([
            ('in_vert', '2f4'),
            ('in_color', '4f4'),
            ('in_linewidth', 'f4'),
        ])
    )


#: Construct a VAO for rendering the fill of shapes
shape_vao = partial(color_vao, moderngl.TRIANGLES)


class Circle(AbstractShape):
    """A circle drawn with lines."""

    __slots__ = (
        'layer', 'segments',
        '_radius',
        'orig_verts',
    )

    def __init__(
            self,
            layer,
            pos=(0, 0),
            radius=100,
            color=(1, 1, 1, 1),
            stroke_width=1.0,
            segments=None):
        super().__init__()
        self.layer = layer
        self.segments = segments or max(4, round(math.pi * radius))
        self.pos = pos
        self._stroke_width = stroke_width

        # Generate verts now
        theta = np.linspace(0, 2 * np.pi, self.segments).reshape((-1, 1))
        self.base_verts = np.hstack([
            np.cos(theta),
            np.sin(theta),
        ]).astype('f4')

        # There's a duplicate vertex so move the first vertex to the center
        self.base_verts[0][:2] = 0

        # Placeholder for scaled verts
        self.orig_verts = np.ones((self.segments, 3), dtype='f4')

        # Assigning radius generates self.orig_verts
        self.radius = radius

        self._color = convert_color(color)
        self._set_dirty()

    def _on_set_radius(self):
        np.multiply(
            self.base_verts,
            self._radius,
            self.orig_verts[:, :2]
        )
        self._set_dirty()

    radius = CallbackProp(_on_set_radius)

    def _stroke_indices(self):
        """Indexes for drawing the stroke as a LINE_STRIP."""
        n = self.segments
        return np.array(
            [n - 1, *range(1, n), 1, 2],
            dtype='i4'
        )

    def _fill_indices(self):
        """Indexes for drawing the fill as TRIANGLES."""
        idxs = np.array([
            (0, i, i + 1)
            for i in range(1, self.segments)
        ], dtype='i4')
        idxs[-1][2] = 1
        return idxs.reshape((-1))

    @property
    def bounds(self):
        x, y = self.pos
        r = self.radius * self.scale
        return ZRect(
            (x - r, y - r),
            (r * 2, r * 2),
        )
