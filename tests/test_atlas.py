"""Tests for packing sprites into a texture atlas."""
import random
from itertools import combinations, product

import pytest
from pygame import Rect

from wasabi2d.atlas import Packer


rng = random.Random(0)


def normal(mean, sd):
    """Return a normally distributed random number >= 1."""
    return max(rng.normalvariate(mean, sd), 1)


# Create 500 rects with dimensions modelled on font glyphs
FONT_GLYPH_RECTS = [
    Rect(0, 0, normal(13, 4), normal(18, 4))
    for _ in range(500)
]


# Create 500 rects with more diverse dimensions
SPRITE_RECTS = [
    Rect(0, 0, normal(50, 50), normal(50, 50))
    for _ in range(500)
]


PACKERS = {
    'MaxRects': lambda: Packer.new_maxrects(threshold=16),
    'Shelves': Packer.new_shelves
}
LISTS = {
    'sprites': SPRITE_RECTS,
    'glyphs': FONT_GLYPH_RECTS,
}
NAMES = [f'{pname} {lname}' for pname, lname in product(PACKERS, LISTS)]
packs = {}


def pack_all(packer, rects):
    """Pack all rects using packer, and return a list of rects by bin id."""
    by_bin = {}
    for r in rects:
        bin, loc = packer.add(Rect(r))
        by_bin.setdefault(bin, []).append(loc)
    return by_bin


def setup_module():
    """Perform the packs now."""
    combos = product(PACKERS.items(), LISTS.items())
    for (pname, packer), (lname, rects) in combos:
        name = f'{pname} {lname}'
        packs[name] = pack_all(packer(), rects)


@pytest.mark.parametrize("pack", NAMES)
def test_within_bounds(pack):
    """Rects packed by the packers lie within the texture bounds."""
    by_bin = packs[pack]

    bounds = Rect(0, 0, 512, 512)
    for bin_id, rects in by_bin.items():
        for r in rects:
            if not bounds.contains(r):
                raise AssertionError(f"{r} is not within bounds {bounds}")


@pytest.mark.parametrize("pack", NAMES)
def test_no_overlap(pack):
    """Rects packed by the packers do not overlap with each other."""
    by_bin = packs[pack]
    for rects in by_bin.values():
        for ra, rb in combinations(rects, 2):
            if ra.colliderect(rb):
                raise AssertionError(f"{ra} collides with {rb}")
