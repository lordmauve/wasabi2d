#version 330

out vec4 f_color;
in vec2 uv;
in vec4 color;
uniform sampler2D tex;

void main() {
    f_color = color * texture(tex, uv);
}
