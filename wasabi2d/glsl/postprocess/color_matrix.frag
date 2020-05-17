#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D image;
uniform mat4 color_matrix;

const vec3 GAMMA = vec3(2.2, 2.2, 2.2);
const vec3 INV_GAMMA = 1.0 / GAMMA;

vec3 srgb_to_linear(vec3 rgb) {
    return pow(rgb, GAMMA);
}

vec3 linear_to_srgb(vec3 lrgb) {
    return pow(lrgb, INV_GAMMA);
}

void main()
{
    vec4 frag = texture(image, uv);
    vec3 rgb = frag.rgb;
    if (frag.a > 1e-6) {
        rgb /= frag.a;
    }
    vec4 converted = vec4(srgb_to_linear(rgb), frag.a) * color_matrix;
    f_color = vec4(linear_to_srgb(converted.rgb), converted.a);
}

