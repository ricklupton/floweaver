"""Helpers for assertions.

For example:

>>> 3 == inst(int)
True
>>> 3 == inst(str)
False
>>> Matcher == inst(type, __name__="Matcher")
True

"""


class Matcher:
    """Base class for Matches that defines __ne__ = not __eq__."""
    def __ne__(self, other):
        return not self.__eq__(other)


class inst(Matcher):
    """Matcher that checks an object isntance has attrs."""

    def __init__(self, cls, **kwargs):
        self._cls = cls
        self._attrs = kwargs

    def __eq__(self, other):
        if not isinstance(other, self._cls):
            return False
        for k, v in self._attrs.items():
            if getattr(other, k) != v:
                return False
        return True

    def __repr__(self):
        kwlist = ", ".join(f"{k}={v!r}" for k, v in self._attrs.items())
        if kwlist:
            kwlist = " with " + kwlist
        return f"<instance of {self._cls.__name__}{kwlist}>"
