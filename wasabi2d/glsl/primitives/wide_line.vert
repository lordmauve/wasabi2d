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
