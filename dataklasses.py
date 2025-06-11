# (modified)

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

from functools import lru_cache, reduce


def codegen(func):
    @lru_cache
    def make_func_code(num_fields, *args):
        fields = tuple(f"_{x}" for x in range(1, 1 + num_fields))
        d = {}
        exec(func(fields, *args), globals(), d)
        return d.popitem()[1]

    return make_func_code


def patch_fields(func, fields):
    co_names = tuple(fields.get(x, x) for x in func.__code__.co_names)
    co_varnames = tuple(fields.get(x, x) for x in func.__code__.co_varnames)
    co_consts = tuple(fields.get(x, x) for x in func.__code__.co_consts)
    new_func = type(func)(
        func.__code__.replace(
            co_names=co_names, co_varnames=co_varnames, co_consts=co_consts
        ),
        func.__globals__,
    )
    new_func.__defaults__ = func.__defaults__
    if func.__kwdefaults__:
        new_func.__kwdefaults__ = {fields[n]: v for n, v in func.__kwdefaults__.items()}
    return new_func


def get_fields(cls):
    names = reduce(lambda x, y: getattr(y, "__annotations__", {}) | x, cls.__mro__, {})
    fields = {f"_{n}": x for n, x in enumerate(names, start=1)}

    slots = getattr(cls, "__slots__", ())
    defaults = {}
    for x in names:
        if x in slots:
            continue
        try:
            defaults[x] = getattr(cls, x)
        except AttributeError:
            pass
    invert = {v: k for k, v in fields.items()}
    defaults = tuple((invert[k], v) for k, v in defaults.items())

    return fields, defaults


def param_list(fields, defaults):
    defaults = dict(defaults)
    params = []
    seen_default = False
    kw_only = False
    for name in fields:
        if name in defaults:
            params.append(f"{name}={defaults[name]!r}")
            seen_default = True
        else:
            # This parameter does not have a default, but a prior parameter did.
            # Switch to keyword-only (if not already).
            if seen_default and not kw_only:
                kw_only = True
                params.append("*")
            params.append(name)
    return ", ".join(params)


@codegen
def make__init__(fields, defaults):
    code = f"def __init__(self, { param_list(fields, defaults) }):\n"
    code += "".join(f"    self.{name} = {name}\n" for name in fields)
    return code


@codegen
def make__new__(fields, defaults):
    code = f"def __new__(cls, { param_list(fields, defaults) }):\n"
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
def make__repr__keyword(fields):
    code = "def __repr__(self):\n"
    code += "    return f'''{type(self).__name__}({"
    if len(fields) == 1:
        t = f"(self.{fields[0]},)"
    else:
        t = "(" + ", ".join(f"self.{n}" for n in fields) + ")"
    code += f"', '.join(f'{{n}}={{v!r}}' for n, v in zip(self.__match_args__, {t}))"
    code += "})'''\n"
    return code


@codegen
def make__eq__(fields):
    self_vals = ", ".join(f"self.{name}" for name in fields)
    other_vals = ", ".join(f"other.{name}" for name in fields)
    code = "def __eq__(self, other):\n"
    code += "    if self.__class__ is other.__class__:\n"
    code += f"        return ({self_vals},) == ({other_vals},)\n"
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
    self_vals = ", ".join(f"self.{name}" for name in fields)
    code = "def __hash__(self):\n"
    code += f"    return hash(({self_vals},))\n"
    return code


def frozen_setattr(self, name, value):
    raise TypeError(f"dataklass(frozen=True) cannot set attribute {name}")


def frozen_delattr(self, name):
    raise TypeError(f"dataklass(frozen=True) cannot delete attribute {name}")


def dataklass(cls=None, *, frozen=False, iter=False, hash=False, keyword_repr=True):
    if cls is None:
        return lambda cls: dataklass(
            cls, frozen=frozen, iter=iter, hash=hash, keyword_repr=keyword_repr
        )

    fields, defaults = get_fields(cls)
    if not fields:
        raise TypeError("dataklass must have at least one annotated field")
    num_fields = len(fields)
    cls_dict = vars(cls)

    cls.__match_args__ = tuple(fields.values())

    if "__init__" not in cls_dict and not frozen:
        cls.__init__ = patch_fields(make__init__(num_fields, defaults), fields)
    if frozen:
        if "__setattr__" in cls_dict or "__delattr__" in cls_dict:
            raise TypeError(
                "dataklass(frozen=True) cannot use __setattr__ or __delattr__"
            )
        cls.__new__ = patch_fields(make__new__(num_fields, defaults), fields)
        cls.__setattr__ = frozen_setattr
        cls.__delattr__ = frozen_delattr

    if "__repr__" not in cls_dict:
        make_repr = make__repr__keyword if keyword_repr else make__repr__
        cls.__repr__ = patch_fields(make_repr(num_fields), fields)

    if "__eq__" not in cls_dict:
        cls.__eq__ = patch_fields(make__eq__(num_fields), fields)

    if iter:
        if "__iter__" in cls_dict:
            raise TypeError("dataklass(iter=True) hides cls.__iter__")
        cls.__iter__ = patch_fields(make__iter__(num_fields), fields)

    if hash:
        if "__hash__" in cls_dict:
            raise TypeError("dataklass(hash=True) hides cls.__hash__")
        cls.__hash__ = patch_fields(make__hash__(num_fields), fields)

    return cls
