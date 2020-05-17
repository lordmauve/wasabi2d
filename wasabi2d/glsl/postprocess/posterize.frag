#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2D image;
uniform int levels;
uniform float gamma;

vec3 posterize(vec3 color) {
    vec3 gammac = pow(color, vec3(gamma, gamma, gamma));
    vec3 post = floor(gammac * levels + vec3(0.5, 0.5, 0.5)) / levels;
    float inv_g = 1.0 / gamma;
    return pow(post, vec3(inv_g, inv_g, inv_g));
}

void main()
{
    vec4 frag = texture(image, uv);
    if (frag.a < 1e-6) {
        discard;
    }
    f_color = vec4(posterize(frag.rgb / frag.a), frag.a);
}
