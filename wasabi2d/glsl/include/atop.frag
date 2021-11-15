
/* Porter-Duff ATOP blending. */
vec4 atop(vec4 top, vec4 bottom) {
    return vec4(
        mix(bottom.rgb, top.rgb, top.a),
        top.a + (1 - top.a) * bottom.a
    );
}
