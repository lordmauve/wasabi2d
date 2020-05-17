#version 330 core
layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

in mat2 rots[];
in vec4 g_color[];
in float size[];
in float age[];
out vec4 color;
out vec2 uv;

uniform mat4 proj;
uniform sampler2D color_tex;
uniform float max_age;
uniform float grow;

void main() {
    float age_frac = clamp(age[0] / max_age, 0.0, 511.0 / 512.0);
    color = g_color[0] * texture(color_tex, vec2(age_frac, 0.0));
    vec2 pos = gl_in[0].gl_Position.xy;
    mat2 rot = rots[0];

    float sz = size[0] * pow(grow, age[0]);

    // Vector to the corner
    vec2 corners[4] = vec2[4](
        vec2(-sz, sz),
        vec2(sz, sz),
        vec2(-sz, -sz),
        vec2(sz, -sz)
    );
    vec2 uvs[4] = vec2[4](
        vec2(0, 0),
        vec2(1, 0),
        vec2(0, 1),
        vec2(1, 1)
    );

    for (int i = 0; i < 4; i++) {
        gl_Position = proj * vec4(pos + rot * corners[i], 0.0, 1.0);
        uv = uvs[i];
        EmitVertex();
    }
    EndPrimitive();
}

