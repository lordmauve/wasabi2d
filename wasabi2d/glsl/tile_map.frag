#version 330

out vec4 f_color;
flat in uint frag_tilemap_block;
in vec2 uv;

uniform usampler2D tiles;
uniform usampler2D tilemap_coords;
uniform sampler2D tex;


/* Given integer coordinates, return float coordinates in [0, 1] */
vec2 to_frac_coords(uvec2 uv) {
    return vec2(uv) / textureSize(tex, 0);
}


void main() {
    ivec2 cell = ivec2(floor(uv * 64.0));
    vec2 tileuv = fract(uv * 64.0);

    cell += ivec2(frag_tilemap_block, 0) * 64;

    uint tilenum = texelFetch(tiles, cell, 0).r;

    uvec4 tc01 = texelFetch(tilemap_coords, ivec2(tilenum, 0), 0);
    uvec4 tc23 = texelFetch(tilemap_coords, ivec2(tilenum, 0), 1);

    vec2 tl = to_frac_coords(tc01.xy);
    mat2 tilespace = mat2(
        to_frac_coords(tc01.zw) - tl,
        to_frac_coords(tc23.xy) - tl
    );

    f_color = texture(tex, tl + tilespace * tileuv);
}
