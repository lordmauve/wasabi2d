#version 330 core

#include "postprocess.glsl"

uniform sampler2D fb;

uniform float factor;

const vec2 center = vec2(0.5, 0.5);

void main()
{
    vec2 off = uv - center;

    float dist = pow(length(off) * 2, factor) / 2;

    off = dist * normalize(off);

    f_color = texture(fb, center + off);
}


