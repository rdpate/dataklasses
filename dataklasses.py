# (see https://github.com/rdpate/dataklasses regarding modifications)

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

__all__ = ["dataklass"]

from functools import lru_cache, reduce, partial, wraps


def codegen(func):
    @lru_cache
    def make_func_code(fields):
        exec(func(fields), globals(), d := {})
        return d.popitem()[1]

    return make_func_code


def patch_attributes(func, fields):
    co_names = tuple(fields.get(x, x) for x in func.__code__.co_names)
    return type(func)(func.__code__.replace(co_names=co_names), func.__globals__)


def patch_args_and_attributes(func, fields):
    co_names = tuple(fields.get(x, x) for x in func.__code__.co_names)
    co_varnames = tuple(fields.get(x, x) for x in func.__code__.co_varnames)
    return type(func)(
        func.__code__.replace(co_names=co_names, co_varnames=co_varnames),
        func.__globals__,
    )


def patch__new__(func, fields):
    co_names = tuple(fields.get(x, x) for x in func.__code__.co_names)
    co_varnames = tuple(fields.get(x, x) for x in func.__code__.co_varnames)
    co_consts = tuple(fields.get(x, x) for x in func.__code__.co_consts)
    return type(func)(
        func.__code__.replace(
            co_names=co_names, co_varnames=co_varnames, co_consts=co_consts
        ),
        func.__globals__,
    )


def get_fields(cls):
    fields = reduce(lambda x, y: getattr(y, "__annotations__", {}) | x, cls.__mro__, {})
    fields = {f"_{n}": x for n, x in enumerate(fields, start=1)}
    return fields


@codegen
def make__init__(fields):
    code = "def __init__(self, " + ",".join(fields) + "):\n"
    code += "".join(f"    self.{name} = {name}\n" for name in fields)
    return code


@codegen
def make__new__(fields):
    code = "def __new__(cls, " + ",".join(fields) + "):\n"
    code += "    self = object.__new__(cls)\n"
    code += "".join(
        f"    object.__setattr__(self, {name!r}, {name})\n" for name in fields
    )
    code += "    return self\n"
    return code


@codegen
def make__repr__(fields):
    code = "def __repr__(self):\n"
    code += "    return f'{type(self).__name__}("
    code += ", ".join(f"{{self.{name}!r}}" for name in fields)
    code += ")'\n"
    return code


@codegen
def make__eq__(fields):
    selfvals = ", ".join(f"self.{name}" for name in fields)
    othervals = ", ".join(f"other.{name}" for name in fields)
    code = "def __eq__(self, other):\n"
    code += "    if self.__class__ is other.__class__:\n"
    code += f"        return ({selfvals},) == ({othervals},)\n"
    code += "    else:\n"
    code += "        return NotImplemented\n"
    return code


@codegen
def make__iter__(fields):
    code = "def __iter__(self):\n"
    code += "".join(f"   yield self.{name}\n" for name in fields)
    return code


@codegen
def make__hash__(fields):
    selfvals = ", ".join(f"self.{name}" for name in fields)
    code = "def __hash__(self):\n"
    code += f"    return hash(({selfvals},))\n"
    return code


def frozen_setattr(self, name, value):
    raise TypeError(f"dataklass(frozen=True) cannot set attribute {name}")


def frozen_delattr(self, name):
    raise TypeError(f"dataklass(frozen=True) cannot delete attribute {name}")


def dataklass(cls=None, *, frozen=False, iter=False, hash=False):
    if cls is None:
        return partial(dataklass, frozen=frozen, iter=iter, hash=hash)
    fields = get_fields(cls)
    if not fields:
        raise TypeError("dataklass must have at least one annotated field")
    placeholders = tuple(fields)
    clsdict = vars(cls)
    if "__init__" not in clsdict and not frozen:
        cls.__init__ = patch_args_and_attributes(make__init__(placeholders), fields)
    if frozen:
        cls.__new__ = patch__new__(make__new__(placeholders), fields)
        if "__setattr__" in clsdict or "__delattr__" in clsdict:
            raise TypeError(
                "dataklass(frozen=True) cannot use __setattr__ or __delattr__"
            )
        cls.__setattr__ = frozen_setattr
        cls.__delattr__ = frozen_delattr
    if "__repr__" not in clsdict:
        cls.__repr__ = patch_attributes(make__repr__(placeholders), fields)
    if "__eq__" not in clsdict:
        cls.__eq__ = patch_attributes(make__eq__(placeholders), fields)
    if iter:
        if "__iter__" in clsdict:
            raise TypeError("dataklass(iter=True) hides cls.__iter__")
        cls.__iter__ = patch_attributes(make__iter__(placeholders), fields)
    if hash:
        if "__hash__" in clsdict:
            raise TypeError("dataklass(hash=True) hides cls.__hash__")
        cls.__hash__ = patch_attributes(make__hash__(placeholders), fields)
    cls.__match_args__ = tuple(fields.values())
    return cls
