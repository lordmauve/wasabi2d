#version 330 core

#include "postprocess.glsl"
uniform sampler2D image;
uniform int pxsize;

void main()
{
    f_color = texture(image, uv / pxsize);
}

