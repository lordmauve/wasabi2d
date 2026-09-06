#version 330 core

#include "postprocess.glsl"

uniform sampler2D image;

uniform float gamma;
uniform float alpha;

#include "gaussian.glsl"

vec3 sample(vec2 pos) {
    vec3 val = texture(image, uv + pos).rgb;
    float lum = dot(val, vec3(0.3, 0.6, 0.1));
    float intensity = pow(lum, gamma);
    return val * intensity;
}

void main()
{
    vec2 tex_offset = 1.0 / textureSize(image, 0); // gets size of single texel
    vec3 result = texture(image, uv).rgb; // current fragment's contribution

    vec2 lookup_stride = tex_offset * blur_direction;
    float weight;
    int irad = int(radius);
    for(int i = 1; i <= irad; ++i)
    {
        weight = gauss(i);
        result += sample(lookup_stride * i) * weight;
        result += sample(lookup_stride * -i) * weight;
    }
    f_color = vec4(result / radius * 2, alpha);
}
