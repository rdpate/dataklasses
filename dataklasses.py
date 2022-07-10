# dataklasses.py
#
#     https://github.com/dabeaz/dataklasses
#
# Author: David Beazley (@dabeaz).
#         http://www.dabeaz.com
#
# Copyright (C) 2021-2022.
#
# Permission is granted to use, copy, and modify this code in any
# manner as long as this copyright message and disclaimer remain in
# the source code.  There is no warranty.  Try to use the code for the
# greater good.

__all__ = ["dataklass", "unfreeze"]

from functools import lru_cache, reduce, partial, wraps

def codegen(func):
    @lru_cache
    def make_func_code(numfields):
        names = [f"_{n}" for n in range(numfields)]
        exec(func(names), globals(), d := {})
        return d.popitem()[1]
    return make_func_code

def patch_args_and_attributes(func, fields, start=0):
    return type(func)(
        func.__code__.replace(
            co_names=(*func.__code__.co_names[:start], *fields),
            co_varnames=("self", *fields)),
        func.__globals__)

def patch_attributes(func, fields, start=0):
    return type(func)(
        func.__code__.replace(co_names=(*func.__code__.co_names[:start], *fields)),
        func.__globals__)

def all_hints(cls):
    return reduce(lambda x, y: getattr(y, "__annotations__", {}) | x, cls.__mro__, {})

@codegen
def make__init__(fields):
    code = "def __init__(self, " + ",".join(fields) + "):\n"
    code += "".join(f" self.{name} = {name}\n" for name in fields)
    return code

@codegen
def make__repr__(fields):
    return (
        "def __repr__(self):\n"
        " return f'{type(self).__name__}("
        + ", ".join("{self." + name + "!r}" for name in fields)
        + ")'\n")

@codegen
def make__eq__(fields):
    selfvals = ",".join(f"self.{name}" for name in fields)
    othervals = ",".join(f"other.{name}" for name in fields)
    return (
        "def __eq__(self, other):\n"
        "  if self.__class__ is other.__class__:\n"
        f"    return ({selfvals},) == ({othervals},)\n"
        "  else:\n"
        "    return NotImplemented\n")

@codegen
def make__iter__(fields):
    return "def __iter__(self):\n" + "".join(
        f"   yield self.{name}\n" for name in fields)

@codegen
def make__hash__(fields):
    self_tuple = "(" + ",".join(f"self.{name}" for name in fields) + ",)"
    return f"def __hash__(self):\n    return hash({self_tuple})\n"

class unfreeze:
    def __init__(self, obj):
        self.obj = obj
    def __enter__(self):
        object.__setattr__(self.obj, "_Frozen", False)
        return self.obj
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.obj._Frozen = True
def frozen_init(func):
    @wraps(func)
    def wrapper(self, *args, **kwds):
        with unfreeze(self):
            func(self, *args, **kwds)
    return wrapper
def frozen_setattr(self, name, value):
    if self._Frozen:
        raise AttributeError(f"frozen dataklass cannot assign field {name}")
    object.__setattr__(self, name, value)
def frozen_delattr(self, name):
    if self._Frozen:
        raise AttributeError(f"frozen dataklass cannot delete field {name}")
    object.__delattr__(self, name)

def dataklass(cls=None, *, frozen=False, iter=False, hash=False):
    if cls is None:
        return partial(dataklass, frozen=frozen, iter=iter, hash=hash)
    fields = all_hints(cls)
    nfields = len(fields)
    clsdict = vars(cls)
    if not fields:
        raise TypeError("dataklass must have at least one annotated field")
    if "__init__" not in clsdict:
        cls.__init__ = patch_args_and_attributes(make__init__(nfields), fields)
    if frozen:
        cls.__init__ = frozen_init(cls.__init__)
        if "__setattr__" in clsdict or "__delattr__" in clsdict:
            raise TypeError("frozen dataklass cannot use __setattr__ or __delattr__")
        cls.__setattr__ = frozen_setattr
        cls.__delattr__ = frozen_delattr
    if "__repr__" not in clsdict:
        cls.__repr__ = patch_attributes(make__repr__(nfields), fields, 2)
    if "__eq__" not in clsdict:
        cls.__eq__ = patch_attributes(make__eq__(nfields), fields, 1)
    if iter and "__iter__" not in clsdict:
        cls.__iter__ = patch_attributes(make__iter__(nfields), fields)
    if hash and "__hash__" not in clsdict:
        cls.__hash__ = patch_attributes(make__hash__(nfields), fields, 1)
    cls.__match_args__ = tuple(fields)
    return cls
