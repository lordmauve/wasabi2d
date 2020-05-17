#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;
//uniform sampler2D gauss_tex;
uniform float radius;
uniform vec2 blur_direction;

uniform float gamma;
uniform float alpha;


float gauss(float off) {
    float x = off / radius * 2;
    return exp(x * x / -2.0);
}


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
