"""Texture packing algorithms."""
from typing import Tuple, Iterable
from itertools import product
from operator import attrgetter

from pygame import Rect


class NoFit(Exception):
    """The block does not fit inside a texture."""


class BaseTex:
    """Base class for packing algorithms.

    In all cases the approach is the same:

    * consider placing the rect into each of the "free" regions.
    * score each of these and pick the best
    * update the free regions based on the selected solution

    The algorithms differ in how they score each solution and how they manage
    available free regions after a placement.

    Note that *Tex classes do not keep track of the *allocated* objects within
    them, only the free space.

    """
    def __init__(self, size: int = 512):
        self.bounds = Rect(0, 0, size, size)
        self.free = [Rect(self.bounds)]

    def _solutions(self, r: Rect) -> Iterable[Tuple[Rect, Rect]]:
        """Iterate over possible locations for r in this texture."""
        rotations = [r]
        if r.h != r.w:
            rotations.append(Rect(0, 0, r.h, r.w))

        return self._validate(product(rotations, self.free))

    def _validate(self,
                  solutions: Iterable[Tuple[Rect, Rect]]
                  ) -> Iterable[Tuple[Rect, Rect]]:
        """Check to see if solutions are valid."""
        for r, block in solutions:
            if block.w >= r.w and block.h >= r.h:
                yield r, block

    def _fitness(self, sol: Tuple[Rect, Rect]) -> float:
        """Return a value indicating the fitness of this location.

        sol is a tuple of (rect, free_region).

        Lower is better; the minimal value will be picked.
        """
        raise NotImplementedError("Subclasses must implement _fitness().")

    def _manage_free(self, rect: Rect, block: Rect):
        """Update the free lists given that rect has been placed into block."""
        raise NotImplementedError("Subclasses must implement _manage_free().")

    def place(self, r: Rect) -> Rect:
        """Place r into this texture.

        Raise NoFit if space could not be found.
        """
        if not self.free:
            raise NoFit()

        try:
            r, block = min(
                self._solutions(r),
                key=self._fitness
            )
        except ValueError as e:
            if e.args[0] != 'min() arg is an empty sequence':
                raise
            raise NoFit() from None

        r.topleft = block.topleft
        self._manage_free(Rect(r), block)
        return r


class MaxRectsTex(BaseTex):
    """Implement the MaxRects algorithm.

    MaxRects tracks all available space in a texture, potentially in very long
    list of overlapping free regions. Adding a rect partitions any intersecting
    free regions so that they do not intersect - potentially creating up to
    4 new free regions for each intersecting free region.

    Packing is very good but can be very slow, particularly when the size of
    rects requested is a small fraction of the available space; this tends to
    create very large numbers of free regions.

    This implementation takes around 40ms to pack 500 randomly sized sprites,
    but as much as 4100ms to pack 500 font glyphs with a low size distribution.

    To control this growth a parameter threshold limits the size of areas we
    keep track of. An area whose smallest dimension is less than threshold is
    not tracked - possibly other larger overlapping regions contain some of the
    space. Threshold values between 16 and 32 give significant speedups without
    badly affecting packing efficiency.

    A reasonable description of MaxRects is here:

    https://eatplayhate.me/2013/09/17/adventures-in-engine-construction-rectangle-packing/

    """

    def __init__(self, size: int = 512, threshold: int = 0):
        self.largest_dim = size
        self.threshold = threshold
        super().__init__(size)

    def _validate(self, solutions):
        for r, block in solutions:
            if block.w < r.w:
                # We keep list sorted so we can break here
                break
            elif block.h < r.h:
                continue

            yield r, block

    def _fitness(self, sol):
        """Return a value indicating the fitness of this localstion.

        Lower is better; the minimal value will be picked.
        """
        r, block = sol
        # Best short side fit
        if r.w < r.h:
            return block.w - r.w
        else:
            return block.h - r.h

    def _manage_free(self, r, _):
        new_free = []  # new rects already checked against threshold
        new_rects = []  # new rects to be checked
        for block in self.free:
            if not block.colliderect(r):
                new_free.append(block)
                continue

            new_rects.extend([
                # Above r
                Rect(block.left, block.top, block.w, r.top - block.top),
                # Below r
                Rect(block.left, r.bottom, block.w, block.bottom - r.bottom),
                # Left of r
                Rect(block.left, block.top, r.left - block.left, block.h),
                # Right of r
                Rect(r.right, block.top, block.right - r.right, block.h),
            ])

        new_free += [
            r for r in new_rects
            if min(r.size) > self.threshold
        ]

        # This is O(n²) but I couldn't improve it by a sort-and sweep approach
        # due to high constant factors
        self.free = [
            r for r in new_free
            if not any(b.contains(r) for b in new_free if b is not r)
        ]
        self.free.sort(key=attrgetter('w'), reverse=True)


class ShelvesTex(BaseTex):
    """Use the shelf algorithm to pack a texture.

    Shelves split the vertical space into "shelf" regions and split the
    horizontal space among objects on a shelf.

    While it wastes more space than MaxRects, this algorithm is much faster.

    This implementation takes around ~10ms to pack 500 font-glyph-size objects
    and a similar amount of time to pack 500 more randomly sized sprites. In
    the case of packing font glyphs, where the size distribution is small, the
    packs are also relatively tight.
    """

    def __init__(self, size=512):
        self.bounds = Rect(0, 0, size, size)
        self.contents = []
        self.free = [Rect(self.bounds)]

    def _validate(self, solutions):
        """Validate the solutions.

        We override this to add a termination condition.
        """
        for r, block in solutions:
            if block.h < r.h:
                # We keep list sorted so we can break here
                break
            elif block.w < r.w:
                continue

            yield r, block

    def _fitness(self, sol):
        """Return a value indicating the fitness of this localstion.

        Lower is better; the minimal value will be picked.
        """
        r, block = sol
        if block.left == 0:
            # Weight creating a new shelf
            return r.h * 0.2
        return block.h - r.h

    def _manage_free(self, r, block):
        if block.left == 0:
            # Allocating a new shelf
            top = block.top
            block.height -= r.height
            block.top = r.bottom
            if block.w > r.w:
                self.free.append(Rect(r.right, top, block.w - r.w, r.h))
            if block.height <= 0:
                self.free.remove(block)
        else:
            block.width -= r.width
            block.left = r.right
            if block.width <= 0:
                self.free.remove(block)

        self.free.sort(key=attrgetter('h'), reverse=True)


class Packer:
    """A collection of texture bins with associated packers."""

    @classmethod
    def new_maxrects(cls, size=512, threshold=0):
        """Create a new packer using the MaxRects algorithm."""
        return cls(
            tex_factory=lambda: MaxRectsTex(
                size=size,
                threshold=threshold
            )
        )

    @classmethod
    def new_shelves(cls, size=512):
        """Create a new packer using the Shelves algorithm."""
        return cls(tex_factory=lambda: ShelvesTex(size))

    def __init__(self, tex_factory):
        self.texs = []
        self.new_tex = tex_factory

    def add(self, r: Rect) -> Tuple[int, Rect]:
        """Pack a new rectangle.

        Return a tuple of (bin ID, rect).
        """
        i = -1
        for i, t in enumerate(self.texs):
            try:
                result = t.place(r)
            except NoFit:
                continue
            else:
                return i, result
        new = self.new_tex()
        result = new.place(r)
        self.texs.append(new)
        return i + 1, result
