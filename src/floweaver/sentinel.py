#!/usr/bin/env python
# coding: utf-8

"""
Create sentinel and singleton objects.

Copyright 2014 © Eddie Antonio Santos. MIT licensed.
"""

import inspect

__all__ = ['create']
__version__ = '0.1.1'


def get_caller_module():
    """
    Returns the name of the caller's module as a string.

    >>> get_caller_module()
    '__main__'
    """
    stack = inspect.stack()
    assert len(stack) > 1
    caller = stack[2][0]
    return caller.f_globals['__name__']


def create(name, mro=(object,), extra_methods={}, *args, **kwargs):
    """
    create(name, mro=(object,), extra_methods={}, ...) -> Sentinel instance

    Creates a new sentinel instance. This is a singleton instance kind
    of like the builtin None, and Ellipsis.

    Method resolution order (MRO) for the anonymous class can be
    specified (i.e., it can be a subclass). Provide the mro as tuple of
    all classes that it inherits from. If only one class, provide a
    1-tuple: e.g., (Cls,).

    Additionally extra class attributes, such as methods can be provided
    in the extra_methods dict. The following methods are provided, but
    can be overridden:

        __repr__()
            Returns the class name, similar to None and Ellipsis.
        __copy__()
        __deepcopy__()
            Always return the same singleton instance such that
            ``copy(Sentinel) is Sentinel`` is true.
        __reduce__()
            Provided for proper pickling prowess. That is,
            ``pickle.loads(pickle.dumps(Sentinel)) is Sentinel`` is
            true.

    Finally, the remain arguments and keyword arguments are passed to
    the super class's __init__().  This is helpful when for
    instantiating base classes such as a tuple.
    """

    cls_dict = {}

    cls_dict.update(
        # Provide a nice, clean, self-documenting __repr__
        __repr__=lambda self: name,
        # Provide a copy and deepcopy implementation which simply return the
        # same exact instance.
        __deepcopy__=lambda self, _memo: self,
        __copy__=lambda self: self,
        # Provide a hook for pickling the sentinel.
        __reduce__=lambda self: name
    )

    # If the default MRO is given, then it's safe to prevent the singleton
    # instance from having a instance dictionary.
    if mro == (object,):
        cls_dict.update(__slots__=())

    cls_dict.update(extra_methods)

    anon_type = type(name, mro, cls_dict)

    # Stack introspection -- make the singleton always belong to the module of
    # its caller. If we don't do this, pickling using __reduce__() will fail!
    anon_type.__module__ = get_caller_module()

    # Return the singleton instance of this new, "anonymous" type.
    return anon_type(*args, **kwargs)
