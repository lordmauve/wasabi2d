#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D image;
uniform int pxsize;

void main()
{
    f_color = texture(image, uv / pxsize);
}

