/* Blur in one direction (given by blur_direction)
 * Shader code adapted from https://learnopengl.com/Advanced-Lighting/Bloom
 */
#version 330 core

#include "postprocess.glsl"

uniform sampler2D image;

#include "gaussian.glsl"

void main()
{
    vec2 tex_offset = 1.0 / textureSize(image, 0); // gets size of single texel
    vec4 result = texture(image, uv); // current fragment's contribution

    vec2 lookup_stride = tex_offset * blur_direction;
    float weight_sum = 1.0;
    float weight;
    int irad = int(ceil(radius));
    for(int i = 1; i < irad; ++i)
    {
        weight = gauss(i);
        weight_sum += weight * 2;
        result += texture(image, uv + lookup_stride * i) * weight;
        result += texture(image, uv - lookup_stride * i) * weight;
    }
    f_color = result / weight_sum;
}

