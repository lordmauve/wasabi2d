"""An object that connects a graphics primitive with a collision shape."""
from .rect import Rect


ANCHORS = {
    'x': {
        'left': 0.0,
        'center': 0.5,
        'middle': 0.5,
        'right': 1.0,
    },
    'y': {
        'top': 0.0,
        'center': 0.5,
        'middle': 0.5,
        'bottom': 1.0,
    }
}


def calculate_anchor(value, dim, total):
    if isinstance(value, str):
        try:
            return total * ANCHORS[dim][value]
        except KeyError:
            raise ValueError(
                '%r is not a valid %s-anchor name' % (value, dim)
            )
    return float(value)


# These are methods (of the same name) on pygame.Rect
SYMBOLIC_POSITIONS = set((
    "topleft", "bottomleft", "topright", "bottomright",
    "midtop", "midleft", "midbottom", "midright",
    "center",
))


class Actor:
    """Actors are associated with a graphics object and a rectangle.

    We delegate attribute access to the appropriate one, and keep the two
    in sync, transferring position updates to the primitive.

    """

    RECT_ATTRS = set(Rect.VALID_ATTRIBUTES)
    PRIM_ATTRS = {'pos', 'image', 'angle'}

    def __init__(self, prim, pos=None, anchor=None, **kwargs):
        self.prim = prim  # The primitive we are wrapping

        self.__dict__["bounds"] = self.prim.bounds
        # Initialise it at (0, 0) for size (0, 0).
        # We'll move it to the right place and resize it later
        self._init_position(pos, anchor, **kwargs)
        self.prim.pos = self.bounds.center

    def __getattr__(self, name):
        """Delegate attribute access to the ZRect."""
        if name in self.PRIM_ATTRS:
            return getattr(self.prim, name)
        try:
            return getattr(self.bounds, name)
        except AttributeError:
            pass

        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        """Set an attribute.

        If the attribute is one that we know the rect class has, set it and
        then update the position of our primitive.
        """
        if name in self.RECT_ATTRS:
            setattr(self.bounds, name, value)
            self.prim.pos = self.bounds.center
        elif name in self.PRIM_ATTRS:
            setattr(self.prim, name, value)
            if name == 'image':
                self.bounds.size = self.prim.width, self.prim.height
            elif name == 'pos':
                self.bounds.center = self.prim.pos
        else:
            object.__setattr__(self, name, value)

    def _init_position(self, pos, anchor, **kwargs):
        if anchor is None:
            anchor = ("center", "center")
        self.anchor = anchor

        symbolic_pos_args = {
            k: kwargs[k] for k in kwargs if k in SYMBOLIC_POSITIONS}

        if not pos and not symbolic_pos_args:
            # No positional information given, use sensible top-left default
            self.topleft = (0, 0)
        elif pos and symbolic_pos_args:
            raise TypeError(
                "'pos' argument cannot be mixed with 'topleft', "
                "'topright' etc. argument."
            )
        elif pos:
            self.pos = pos
        else:
            self._set_symbolic_pos(symbolic_pos_args)

    def _set_symbolic_pos(self, symbolic_pos_dict):
        if len(symbolic_pos_dict) != 0:
            if len(symbolic_pos_dict) == 0:
                raise TypeError(
                    "No position-setting keyword arguments ('topleft', "
                    "'topright' etc) found."
                )
            if len(symbolic_pos_dict) > 1:
                raise TypeError(
                    "Only one 'topleft', 'topright' etc. argument is allowed."
                )

        setter_name, position = symbolic_pos_dict.popitem()
        setattr(self, setter_name, position)

    def delete(self):
        self.prim.delete()
        self.prim = None
