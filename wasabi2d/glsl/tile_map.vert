#version 330

in ivec2 in_vert;
in uint in_tilemap_block;
out uint tilemap_block;

uniform vec2 block_size;

void main() {
    gl_Position = vec4(in_vert * block_size, 0.0, 1.0);
    tilemap_block = in_tilemap_block;
}
