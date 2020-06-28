#version 330

uniform mat4 proj;

in mat3x2 xform;
in vec2 dims;
in vec4 color;
in mat3x2 uvmap;
in uvec4 cuts;

out mat3x2 g_xform;
out vec2 g_dims;
out vec4 g_color;
out mat3x2 g_uvmap;
out uvec4 g_cuts;


void main() {
    g_xform = xform;
    g_dims = dims;
    g_color = color;
    g_uvmap = uvmap;
    g_cuts = cuts;
}
