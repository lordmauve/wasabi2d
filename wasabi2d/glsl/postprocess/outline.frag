#version 330 core

in vec2 uv;
out vec4 f_color;

uniform sampler2D image;
uniform vec4 color;

vec4 atop(vec4 top, vec4 bottom) {
    return vec4(
        mix(bottom.rgb, top.rgb, top.a),
        top.a + (1 - top.a) * bottom.a
    );
}

void main()
{
    vec2 tex_offset = 1.0 / textureSize(image, 0); // gets size of single texel

    vec4 orig_color = texture(image, uv);

    float coverage = 0.0;
    for(int j = 0; j <= 2; j++) {
        for(int i = 0; i <= 2; i++) {
            if (i != j) {
                vec2 rel = vec2(i - 1, j - 1);
                float in_alpha = texture(image, uv + rel * tex_offset).a;

                coverage += in_alpha / length(rel);
            }
        }
    }
    vec4 outline = vec4(color.rgb, min(1.0, color.a * coverage));

    f_color = atop(orig_color, outline);
}
