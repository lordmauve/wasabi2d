#version 330

uniform mat4 proj;

in vec2 in_vert;
in vec4 in_color;
out vec4 color;

void main() {
    gl_Position = proj * vec4(in_vert, 0.0, 1.0);
    color = in_color;
}
