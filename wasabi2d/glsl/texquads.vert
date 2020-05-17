#version 330

uniform mat4 proj;

in vec2 in_vert;
in vec4 in_color;
in ivec2 in_uv;
out vec2 uv;
out vec4 color;
uniform sampler2D tex;

void main() {
    gl_Position = proj * vec4(in_vert.xy, 0.0, 1.0);
    uv = vec2(in_uv) / textureSize(tex, 0);
    color = in_color;
}

