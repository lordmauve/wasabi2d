#version 330

out vec4 f_color;
flat in uint frag_tilemap_block;
in vec2 uv;

uniform sampler2D tiles;
uniform sampler2D tilemap_coords;
uniform sampler2D tex;


/* Given integer coordinates, return float coordinates in [0, 1] */
vec2 to_frac_coords(vec2 uv) {
    return uv / textureSize(tex, 0);
}


void main() {
    ivec2 cell = ivec2(floor(uv * 64.0));
    vec2 tileuv = fract(uv * 64.0);

    cell += ivec2(frag_tilemap_block, 0) * 64;

    uint tilenum = uint(texelFetch(tiles, cell, 0).r);

    vec4 tc01 = texelFetch(tilemap_coords, ivec2(tilenum, 0), 0);
    vec4 tc23 = texelFetch(tilemap_coords, ivec2(tilenum, 0), 1);

    vec2 tl = to_frac_coords(tc01.xy);
    mat2 tilespace = mat2(
        to_frac_coords(tc01.zw) - tl,
        to_frac_coords(tc23.xy) - tl
    );

    f_color = texture(tex, tl + tilespace * tileuv) + vec4(1.0, 0.0, 0.0, 1.0);
}
