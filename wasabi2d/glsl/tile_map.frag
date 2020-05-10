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
    ivec2 cell = ivec2(floor(uv * 64.0));  // Which tile are we in
    vec2 tileuv = fract(uv * 64.0);  // Where are we in that tile

    // Look up tile for this position
    ivec2 tilemap_pos = cell + ivec2(frag_tilemap_block * 64U, 0);
    uint tilenum = uint(texelFetch(tiles, tilemap_pos, 0).r * 255.0);
    //uint tilenum = frag_tilemap_block;
    if (tilenum == 0U) {
        discard;
    }

    /* Fetch UV coordinates of the tile in the texture. */
    vec2 tl = texelFetch(tilemap_coords, ivec2(0, tilenum), 0).xy;
    vec2 tr = texelFetch(tilemap_coords, ivec2(1, tilenum), 0).xy;
    vec2 bl = texelFetch(tilemap_coords, ivec2(2, tilenum), 0).xy;

    /*
    vec4 tc01 = texelFetch(tilemap_coords, ivec2(tilenum, 0), 0);
    vec4 tc23 = texelFetch(tilemap_coords, ivec2(tilenum, 1), 0);

    vec2 tl = tc01.xy;
    vec2 tr = tc01.zw;
    vec2 bl = tc23.xz;
    vec2 br = tc23.zw;
    */

    mat2 tilespace = mat2(
        tr - tl,
        bl - tl
    );

    f_color = texture(tex, to_frac_coords(tl + tileuv * 64.0));
    //f_color = texture(tex, to_frac_coords(tl + tilespace * tileuv));
}
