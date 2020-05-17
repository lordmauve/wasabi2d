// Shader for a plain color fill
#version 330

out vec4 f_color;
in vec4 color;

void main() {
    f_color = color;
}
