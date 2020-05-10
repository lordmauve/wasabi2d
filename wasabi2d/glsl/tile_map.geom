#version 330
layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

in uint[1] tilemap_block;
flat out uint frag_tilemap_block;
out vec2 uv;

uniform vec2 block_size;
uniform mat4 proj;

const vec2 corners[4] = vec2[4](
    vec2(0.0, 0.0),
    vec2(1.0, 0.0),
    vec2(0.0, 1.0),
    vec2(1.0, 1.0)
);


/* Project a relative vector using the mvp matrix. */
vec2 project_vec(vec2 v) {
    return (proj * vec4(v, 0.0, 0.0)).xy;
}


/* Project a point using the mvp matrix. */
vec2 project_point(vec2 v) {
    return (proj * vec4(v, 0.0, 1.0)).xy;
}


void main() {
    vec4 point = gl_in[0].gl_Position;

    vec2 topleft = project_point(point.xy);
    vec2 tile_x = project_vec(vec2(block_size.x, 0.0));
    vec2 tile_y = project_vec(vec2(0.0, block_size.y));

    vec2 tile_across = tile_x + tile_y;

    /*
    // Cull
    vec2 xform_centre = topleft + tile_across * 4.0;
    float radius = length(tile_across);
    if (all(greaterThan(xform_centre, vec2(1.0 - radius, 1.0 - radius)))) {
        return;
    }
    */

    mat2 tilespace = mat2(tile_x, tile_y);

    frag_tilemap_block = tilemap_block[0];
    for (int c = 0; c < 4; c++) {
        uv = corners[c];
        gl_Position = proj * vec4(topleft + corners[c] * block_size, 0.0, 1.0);

            //vec4(topleft + tilespace * corners[c], 0.0, 0.0);
        EmitVertex();
    }
    EndPrimitive();
}

