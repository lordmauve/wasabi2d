/* Fragment program to copy from multisample texture to non-multisample.
 *
 * This lets us render polygon geometry with multisampling and run
 * postprocessing effects on the anti-aliased output.
 */
#version 330 core

in vec2 uv;
out vec4 f_color;
uniform sampler2DMS image;

uniform int samples = 4;

void main()
{
    vec4 color = vec4(0, 0, 0, 0);

    ivec2 pos = ivec2(uv * textureSize(image));

    for (int i = 0; i < samples; i++) {
        color += texelFetch(image, pos, i);
    }
    if (color.a == 0.0) {
        discard;
    }
    f_color = vec4(
        color.rgb / color.a,
        color.a / samples
    );
}

