/* Shader for drawing glyphs from a font.
 *
 * Slight modification to the textured quads: we only use the texture's alpha
 * channel because pygame pre-multiplies alpha in text rendering.
 */
#version 330

out vec4 f_color;
in vec2 uv;
in vec4 color;
uniform sampler2D tex;

void main() {
    f_color = vec4(color.rgb, color.a * texture(tex, uv).a);
}

