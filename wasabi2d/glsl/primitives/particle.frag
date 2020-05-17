#version 330

out vec4 f_color;
in vec4 color;
in vec2 uv;
uniform sampler2D tex;

void main() {
    f_color = color * texture(tex, uv);
}

