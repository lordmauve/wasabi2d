#version 330 core
layout (lines_adjacency) in;
//layout (triangle_strip, max_vertices = 2) out;
layout (triangle_strip, max_vertices = 4) out;

in vec4 g_color[];
in float widths[];
out vec4 color;

const float MITRE_LIMIT = 6.0;

vec2 rot90(vec2 v) {
    return vec2(-v.y, v.x);
}

bool is_nonzero(vec2 v) {
    return dot(v, v) > 1e-4;
}

uniform mat4 proj;


void mitre(vec2 a, vec2 b, vec2 c, float width) {
    vec2 ab = normalize(b - a);
    vec2 bc = normalize(c - b);

    if (!is_nonzero(ab)) {
        ab = bc;
    }
    if (!is_nonzero(bc)) {
        bc = ab;
    }

    // across bc
    vec2 xbc = rot90(bc);

    vec2 along = normalize(ab + bc);
    vec2 across_mitre = rot90(along);

    float scale = 1.0 / dot(xbc, across_mitre);

    //This kind of works Ok although it does cause the width to change
    // scale = min(scale, MITRE_LIMIT);  // limit extension of the mitre
    vec2 across = width * across_mitre * scale;

    gl_Position = proj * vec4(b + across, 0.0, 1.0);
    EmitVertex();

    gl_Position = proj * vec4(b - across, 0.0, 1.0);
    EmitVertex();
}


void main() {
    color = g_color[1];

    vec2 a = gl_in[0].gl_Position.xy;
    vec2 b = gl_in[1].gl_Position.xy;
    vec2 c = gl_in[2].gl_Position.xy;
    vec2 d = gl_in[3].gl_Position.xy;

    vec2 along = c - b;

    if (is_nonzero(b - a)) {
        mitre(a, b, c, widths[1]);
    } else {
        mitre(b - along, b, c, widths[1]);
    }
    if (is_nonzero(d - c)) {
        mitre(b, c, d, widths[2]);
    } else {
        mitre(b, c, c + along, widths[2]);
    }

    EndPrimitive();
}

