#version 330 core

#include "postprocess.glsl"
uniform sampler2D image;

void main()
{
    f_color = texture(image, uv);
}
