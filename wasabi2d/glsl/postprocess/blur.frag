/* Blur in one direction (given by blur_direction)
 * Shader code adapted from https://learnopengl.com/Advanced-Lighting/Bloom
 */
#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;
uniform float radius;
uniform vec2 blur_direction;


float gauss(float off) {
    float x = off / radius * 2;
    return exp(x * x / -2.0);
}


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

