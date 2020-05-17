#version 330

out vec4 f_color;
flat in uint frag_tilemap_offset;
flat in float lod;
flat in vec2 clamp_min;
in vec2 uv;

uniform sampler2D tiles;
uniform sampler2D tilemap_coords;
uniform sampler2D tex;


/* Given integer coordinates, return float coordinates in [0, 1] */
vec2 to_frac_coords(vec2 texcoord) {
    return texcoord / textureSize(tex, 0);
}

void main() {
    vec2 cell = floor(uv);  // Which tile are we in
    vec2 tileuv = uv - cell;  // Where are we in that tile

    // Look up tile for this position
    ivec2 tilemap_pos = ivec2(cell) + ivec2(frag_tilemap_offset, 0);
    uint tilenum = uint(texelFetch(tiles, tilemap_pos, 0).r * 255.0);
    if (tilenum == 0U) {
        discard;
    }

    /* Fetch UV coordinates of the tile in the texture. */
    vec4 coords0 = texelFetch(tilemap_coords, ivec2(0, tilenum), 0);
    vec2 tl = coords0.xy;
    vec2 across = coords0.zw;
    vec2 down = texelFetch(tilemap_coords, ivec2(1, tilenum), 0).xy;

    // Clamp at edges of this tile
    vec2 mapped_uv = clamp(tileuv, clamp_min, vec2(1.0) - clamp_min);

    // Texture map
    vec2 lookup_uv = to_frac_coords(
        tl + across * mapped_uv.x + down * mapped_uv.y
    );

    f_color = textureLod(tex, lookup_uv, lod);
}
