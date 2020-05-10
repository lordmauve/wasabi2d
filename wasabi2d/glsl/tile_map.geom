#version 330
layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

in uint[1] tilemap_block;
flat out uint frag_tilemap_offset;
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
    vec2 tile_across = project_vec(block_size);

    // Cull
    vec2 xform_centre = topleft + tile_across * 0.5;
    float radius = length(tile_across) * 0.5;
    if (all(greaterThan(abs(xform_centre), vec2(1.0 + radius, 1.0 + radius)))) {
        return;
    }

    frag_tilemap_offset = tilemap_block[0] * 64U;
    for (int c = 0; c < 4; c++) {
        uv = corners[c] * 64.0;
        gl_Position = proj * vec4(topleft + corners[c] * block_size, 0.0, 1.0);

        EmitVertex();
    }
    EndPrimitive();
}

