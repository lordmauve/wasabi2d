#version 330

in vec2 in_vert;
in vec4 in_color;
in float in_size;
in float in_angle;
in float in_age;
out vec4 g_color;
out float size;
out float age;
out mat2 rots;

uniform float max_age;

void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
    g_color = in_color;
    size = in_size;
    age = in_age;

    float c = cos(-in_angle);
    float s = sin(-in_angle);
    rots = mat2(c, -s, s, c);
}

