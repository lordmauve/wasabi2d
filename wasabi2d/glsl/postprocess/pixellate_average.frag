#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;
uniform int pxsize;
uniform vec2 blur_direction;
uniform vec2 uvscale;


void main()
{
    vec2 tex_offset = 1.0 / textureSize(image, 0); // gets size of single texel
    vec4 result = vec4(0, 0, 0, 0);

    vec2 inuv = uv * uvscale;  // uv in the input image
    vec2 lookup_stride = tex_offset * blur_direction;
    for(int i = 0; i < pxsize; i++) {
        float off = i - pxsize / 2;
        result += texture(image, inuv + lookup_stride * off);
    }
    f_color = result / pxsize;
}


