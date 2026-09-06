uniform float radius;
uniform vec2 blur_direction;

float gauss(float off) {
    float x = off / radius * 2;
    return exp(x * x / -2.0);
}
