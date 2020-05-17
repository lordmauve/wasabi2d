#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;
uniform sampler2D blurred;
uniform float radius;
uniform vec2 offset;
uniform float opacity;

const vec3 BLACK = vec3(0, 0, 0);


void main()
{
    vec2 tex_offset = vec2(1.0, -1.0) * offset / textureSize(image, 0);

    vec4 image = texture(image, uv);

    float shadow_a = texture(blurred, uv - tex_offset).a * opacity;

    float alpha = image.a;
    float dest_alpha = alpha + (1 - alpha) * shadow_a;

    f_color = vec4(
        (image.rgb + (1 - alpha) * shadow_a * BLACK) / dest_alpha,
        dest_alpha
    );
}
