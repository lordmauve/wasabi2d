#version 330
layout (points) in;
layout (triangle_strip, max_vertices = 24) out;

uniform mat4 proj;
uniform sampler2D tex;

in mat3x2 g_xform[];
in vec2 g_dims[];
in vec4 g_color[];
in mat3x2 g_uvmap[];
in uvec4 g_cuts[];

out vec2 pos;
out vec2 uv;
out vec4 color;


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

const mat2x3 BASIS = mat2x3(1.0, 0.0, 0.0, 1.0, 0.0, 0.0);


/* Return the dimensions of the sprite */
vec2 dims(mat3x2 uvmap) {
    mat2 xform = uvmap * BASIS;
    return abs(
         xform * vec2(1.0, 1.0)
    );
}


const vec2 ORIGIN = vec2(0, 0);

void main() {

    mat3x2 uvmap = g_uvmap[0];
    vec2 br = abs(g_dims[0] * 0.5);
    vec2 sprite_dims = dims(uvmap);

    // The uvmap is given in pixels; this should give tex coords
    vec2 texsize = textureSize(tex, 0);
    mat3x2 uvxform = uvmap / mat3x2(texsize, texsize, texsize);

    vec2 verts[4];
    verts[0] = -br;
    verts[1] = min(-br + g_cuts[0].xz, ORIGIN);
    verts[2] = max(br - g_cuts[0].yw, ORIGIN);
    verts[3] = br;

    // uvs within the space of the texture
    vec2 uvs[4];
    uvs[0] = vec2(0, 0);
    uvs[1] = g_cuts[0].xz / sprite_dims;
    uvs[2] = g_cuts[0].yw / sprite_dims;
    uvs[3] = vec2(1, 1);

    // Build 4x4 modelviewprojection matrix
    mat3x2 xform = g_xform[0];
    vec3 xform_x = transpose(xform)[0].xyz;
    vec3 xform_y = transpose(xform)[1].xyz;
    mat4 mvp = mat4(
        xform_x.xy, 0.0, xform_x.z,
        xform_y.xy, 0.0, xform_y.z,
        0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    ) * proj;

    color = g_color[0];
    for (int row = 0; row < 3; row++) {
        for (int x = 0; x < 4; x++) {
            for (int y = row; y < row + 1; y++) {
                gl_Position = mvp * vec4(
                    verts[x].x,
                    verts[y].y,
                    0.0,
                    1.0
                );
                uv = uvxform * vec3(
                    uvs[x].x,
                    uvs[y].y,
                    1.0
                );
                EmitVertex();
            }
        }
        EndPrimitive();
    }
}
