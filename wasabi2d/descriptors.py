"""Common descriptors to simplify setting attributes on objects."""


class CallbackProp:
    """Descriptor for a property that calls a callback when set.

    The callback is passed the instance that the attribute was set on.

    """
    __slots__ = ('callback', 'name')

    def __init__(self, callback):
        self.callback = callback
        self.name = None

    def __set_name__(self, cls, name):
        self.name = f'_{name}'

    def __get__(self, inst, cls=None):
        return getattr(inst, self.name)

    def __set__(self, inst, value):
        setattr(inst, self.name, value)
        self.callback(inst)
