#version 330 core

in vec2 uv;
out vec4 f_color;

uniform float alpha;
uniform sampler2D fb;

void main()
{
    vec4 frag = texture(fb, uv);
    f_color = vec4(frag.rgb, frag.a * alpha);
}
