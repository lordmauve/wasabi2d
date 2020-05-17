#version 330 core

out vec4 f_color;

uniform float fade;

void main()
{
    f_color = vec4(0, 0, 0, fade);
}
