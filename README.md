# dataklasses

Dataklasses is a library that allows you to quickly define data
classes using Python type hints. Here's an example of how you use it:

```python
from dataklasses import dataklass

@dataklass
class Coordinates:
    x: int
    y: int
    z: int = 0
```

The resulting class works in a well civilised way, providing the usual
`__init__()`, `__repr__()`, and `__eq__()` methods that you'd normally
have to type out by hand:

```python
>>> a = Coordinates(2, 3)
>>> a
Coordinates(x=2, y=3, z=0)
>>> a.x
2
>>> a.y
3
>>> a.z
0
>>> b = Coordinates(2, 3)
>>> a == b
True
```

It's easy! Almost too easy.

## Wait, doesn't this already exist?

No, it doesn't.  Yes, certain naysayers will be quick to point out the
existence of `@dataclass` from the standard library. Ok, sure, THAT
exists.  However, it's slow and complicated.  Dataklasses are neither
of those things.  The entire `dataklasses` module is less than 100
lines.  The resulting classes import 15-20 times faster than
dataclasses.  See the `perf.py` file for a benchmark.

## Theory of Operation

While out walking with his puppy, Dave had a certain insight about the nature
of Python byte-code.  Coming back to the house, he had to try it out:

```python
>>> def __init1__(self, x, y):
...     self.x = x
...     self.y = y
...
>>> def __init2__(self, foo, bar):
...     self.foo = foo
...     self.bar = bar
...
>>> __init1__.__code__.co_code == __init2__.__code__.co_code
True
```

How intriguing!  The underlying byte-code is exactly the same even
though the functions are using different argument and attribute names.
Aha! Now, we're onto something interesting.

The `dataclasses` module in the standard library works by collecting
type hints, generating code strings, and executing them using the
`exec()` function.  This happens for every single class definition
where it's used. If it sounds slow, that's because it is.  In fact, it
defeats any benefit of module caching in Python's import system.

Dataklasses are different.  They start out in the same manner--code is
first generated by collecting type hints and using `exec()`.  However,
the underlying byte-code is cached and reused in subsequent class
definitions whenever possible. Caching is good.

## A Short Story

Once upon a time, there was this programming language that I'll refer
to as "Lava."  Anyways, anytime you started a program written in Lava,
you could just tell by the awkward silence and inactivity of your
machine before the fans kicked in.  "Ah shit, this is written in Lava"
you'd exclaim.

## Questions and Answers

**Q: What methods does `dataklass` generate?**

A: By default `__init__()`, `__repr__()`, and `__eq__()` methods are generated.
`__match_args__` is also defined to assist with pattern matching.

**Q: Does `dataklass` enforce the specified types?**

A: No. The types are merely clues about what the value might be and
the Python language does not provide any enforcement on its own.

**Q: Are there any additional features?**

A: No. You can either have features or you can have performance. Pick one.

**Q: Does `dataklass` use any advanced magic such as metaclasses?**

A: No.

**Q: How do I install `dataklasses`?**

A: There is no `setup.py` file, installer, or an official release. You
install it by copying the code into your own project. `dataklasses.py` is
small. You are encouraged to modify it to your own purposes.

**Q: What versions of Python does it work with?**

A: The code will work with versions 3.9 and later.

**Q: But what if new features get added?**

A: What new features?  The best new features are no new features.

**Q: Who maintains dataklasses?**

A: If you're using it, you do. You maintain dataklasses.

**Q: Is this actually a serious project?**

A: It's best to think of dataklasses as more of an idea than a project.
There are many tools and libraries that perform some form of code generation.
Dataklasses is a proof-of-concept for a different approach to that.  If you're
a minimalist like me, you'll find it to be perfectly functional.  If you're
looking for a lot of knobs to turn, you should probably move along.

**Q: Should I give dataklasses a GitHub star?**

A: Yes, because it will help me look superior to the other parents with
kids in the middle-school robot club.

**Q: Who wrote this?**

A: `dataklasses` is the work of David Beazley. http://www.dabeaz.com.
