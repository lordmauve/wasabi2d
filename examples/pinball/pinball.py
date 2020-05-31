"""Pinball collision demo.

"""
import wasabi2d as w2d
import random
from pygame.math import Vector2 as v2
from pygame import Rect

from spatial_hash import SpatialHash


scene = w2d.Scene(1280, 720)
scene.chain = [
    w2d.chain.LayerRange(stop=0),
    w2d.chain.DisplacementMap(
        displacement=w2d.chain.Layers([1]),
        paint=w2d.chain.LayerRange(stop=0),
        scale=-100
    )
]

scene.layers[0].set_effect('dropshadow', offset=(3, 3))

cursor = scene.layers[0].add_sprite(
    'cursor',
    anchor_x='left',
    anchor_y='top'
)

scene.layers[-1].add_sprite('wood', anchor_x='left', anchor_y='top')

GRAVITY = v2(0, 1)
BALL_RADIUS = 15
BALL_COLOR = (34, 128, 75)
ELASTICITY = 0.3
SEPARATION_STEPS = [1.0] * 10

BALL_COUNT = 20


class Ball:
    def __init__(self, x, y, radius=15):
        self.sprite = scene.layers[0].add_sprite(
            'steel',
            scale=radius / 32,
        )
        self.refl = scene.layers[1].add_sprite(
            'lens_fresnel',
            scale=radius / 100,
            color=(1, 1, 1, 0.5)
        )
        self.velocity = v2(0, 0)
        self.radius = radius
        self.mass = radius * radius
        dr = v2(radius, radius)
        self.rect = Rect(0, 0, *(dr * 2))

        self.pos = v2(x, y)

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):
        self._pos = self.sprite.pos = self.refl.pos = self.rect.center = pos

    def update(self):
        self.pos += self.velocity
        self.velocity += GRAVITY

    def collides(self, ano):
        minsep = ano.radius + self.radius
        return self.pos.distance_squared_to(ano.pos) < minsep * minsep



sh = SpatialHash()

for _ in range(BALL_COUNT):
    b = Ball(
        x=random.randint(0, scene.width),
        y=random.randint(0, scene.height),
        radius=random.choice([20, 24, 30])
    )
    sh.insert(b)


def apply_impact(a, b):
    """Resolve the collision between two balls.

    Calculate their closing momentum and apply a fraction of it back as impulse
    to both objects.
    """
    ab = b.pos - a.pos
    try:
        ab.normalize_ip()
    except ValueError:
        ab = v2(1, 0)
    rel_momentum = ab.dot(a.velocity) * a.mass - ab.dot(b.velocity) * b.mass

    if rel_momentum < 0:
        return

    rel_momentum *= ELASTICITY

    a.velocity -= ab * rel_momentum / a.mass
    b.velocity += ab * rel_momentum / b.mass


def separate(a, b, frac=0.5):
    """Move a and b apart.

    Return True if they are now separate.
    """
    ab = a.pos - b.pos
    sep = ab.length()
    overlap = a.radius + b.radius - sep
    if overlap <= 0:
        return

    if sep == 0.0:
        ab = v2(1, 0)
    else:
        ab /= sep
    masses = a.mass + b.mass
    if overlap > 1:
        overlap *= frac

    a.pos += ab * (overlap * b.mass / masses)
    b.pos -= ab * (overlap * a.mass / masses)


def collide_plane(ball, norm, dist, bounce=True):
    overlap = dist - ball.pos.dot(norm) + ball.radius
    if overlap > 0:
        ball.pos += norm * overlap
        if bounce:
            ball.velocity -= norm * norm.dot(ball.velocity) * (1.0 + ELASTICITY)

BOUNDS = [
    (v2(0, -1), -scene.height),
    (v2(1, 0), 0),
    (v2(-1, 0), -scene.width),
]

collisions = set()


def update(dt):
    global collisions
    balls = sh.items
    for b in balls:
        b.update()

    for p in BOUNDS:
        for b in balls:
            collide_plane(b, *p)
    sh.rebuild()

    for p in BOUNDS:
        for b in balls:
            collide_plane(b, *p)

    # Find all collisions occurring this frame
    prev_collisions = collisions
    collisions = set()
    for b in balls:
        possible_collisions = sh.query(b.rect)
        for a in possible_collisions:
            if a is b:
                continue
            if a.collides(b):
                if id(a) > id(b):
                    pair = b, a
                else:
                    pair = a, b

                if pair not in prev_collisions:
                    # We only apply the bounce to the velocity the first time
                    # they collide.
                    apply_impact(*pair)
                collisions.add(pair)

    # Apply several iterations to separate the collisions
    moved = set(b for pair in collisions for b in pair)
    for frac in SEPARATION_STEPS:
        collisions = {pair for pair in collisions if separate(*pair, frac)}

@w2d.event
def on_mouse_move(pos):
    cursor.pos = pos
    r = Rect(0, 0, 30, 30)
    r.center = pos
    possible_collisions = sh.query(r)
    for b in possible_collisions:
        sep = b.pos - pos
        sep.scale_to_length(2)
        b.velocity += sep


@w2d.event
def on_mouse_down():
    w2d.clock.unschedule(update)
    w2d.clock.each_tick(update)

update(0)
w2d.run()
