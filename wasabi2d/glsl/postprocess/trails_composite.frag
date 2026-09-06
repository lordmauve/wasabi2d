#version 330 core

#include "postprocess.glsl"

uniform float alpha;
uniform sampler2D fb;

void main()
{
    vec4 frag = texture(fb, uv);
    f_color = vec4(frag.rgb, frag.a * alpha);
}
