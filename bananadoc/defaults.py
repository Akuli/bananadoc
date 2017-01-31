# Copyright (c) 2017 Akuli

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Default dumping hooks and parsing functions.

BananaDoc loads this module automatically when it's imported and this
module exports no public functions, so importing this module yourself is
usually pointless. You may still want to read this module to see what
bananadoc does by default.
"""

import functools
import inspect
import types

try:
    import enum
except ImportError:
    # We are running Python 3.3 without enum34, but we don't need to
    # warn the user about this because the documented modules can't use
    # enums either.
    enum = None

import bananadoc


__all__ = []


class DataSection(bananadoc.Section):

    def __init__(self):
        super().__init__("Other data")
        self.data = []

    @property
    def content(self):
        lines = ['```']
        for name, value in self.data:
            lines.append('%s = `%r`' % (name, value))
        lines.append('```')
        return '\n'.join(lines)

    @content.setter
    def content(self, content):
        # bananadoc.Section.__init__ sets this.
        assert content is None


@bananadoc.parsingfunc
def parse_data(section, name, value):
    try:
        datasect = section._datasection
    except AttributeError:
        datasect = section._datasection = DataSection()
    datasect.data.append((name, value))
    return True


# We need to make sure that the data section is the last section there
# is, so we need this.
@bananadoc.modulehook
def add_datasections(section):
    for sub in section.walk_subs():
        try:
            sub.subs.append(section._datasection)
        except AttributeError:   # no data section
            pass


@bananadoc.parsingfunc
def parse_function(parentsect, name, value):
    if not isinstance(value, types.FunctionType):
        return False
    if value.__doc__ is None:
        raise bananadoc.NoDocstring(parentsect.fullname, name)

    # The title will be like thing(a, b, c).
    section = bananadoc.ObjectSection(
        parentsect.fullname, name, value,
        title=name + str(inspect.signature(value)),
        content=inspect.cleandoc(value.__doc__))
    parentsect.subs.append(section)
    return True


@bananadoc.parsingfunc
def parse_property(parentsect, name, value):
    if not isinstance(value, property):
        return False
    if not isinstance(parentsect.value, type):
        # It's a property, but it's not in a class. Let's document it as
        # data instead.
        return False
    if value.__doc__ is None:
        raise bananadoc.NoDocstring(parentsect.fullname, name)

    sub = bananadoc.ObjectSection(
        parentsect.fullname, name, value,
        title="The %s property" % name,
        content=inspect.cleandoc(value.__doc__))
    parentsect.subs.append(sub)
    return True


def _class_sorting_key(cls, name):
    """A sorting key for sorting the content of a class.

    Everything is prioritized like this:
      1. methods
      2. classmethods
      3. staticmethods
      4. properties
      5. other data
    """
    value = getattr(cls, name)
    if isinstance(value, types.FunctionType):
        return 1, name
    if isinstance(value, classmethod):
        return 2, name
    if isinstance(value, staticmethod):
        return 3, name
    if isinstance(value, property):
        return 4, name
    return 5, name


@bananadoc.parsingfunc
def parse_class(parentsect, classname, cls):
    if not isinstance(cls, type):
        # It's not a class.
        return False
    if enum is not None:
        assert not isinstance(cls, enum.EnumMeta), \
               "the enum parser didn't parse %r" % (cls,)
    if cls.__doc__ is None:
        raise bananadoc.NoDocstring(parentsect.fullname, classname)

    bases = []
    for baseclass in cls.__bases__:
        if baseclass is object or baseclass.__name__.startswith('_'):
            # An implementation detail.
            continue
        if baseclass.__module__ in {parentsect.fullname, 'builtins'}:
            bases.append(baseclass.__name__)
        else:
            bases.append(baseclass.__module__ + '.' + baseclass.__name__)
    displayname = classname
    if bases:
        displayname += '(%s)' % ', '.join(bases)

    section = bananadoc.ObjectSection(
        parentsect.fullname, classname, cls,
        title="class %s" % displayname,
        content=inspect.cleandoc(cls.__doc__))
    parentsect.subs.append(section)

    try:
        names = cls._bananadoc_all
    except AttributeError:
        # We need __dict__ because we don't want anything from parent
        # classes.
        names = [name for name in cls.__dict__
                 if name == '__init__' or not name.startswith('_')]
        names.sort(key=functools.partial(_class_sorting_key, cls))
    for name in names:
        # We need __dict__ because we want real classmethod and
        # staticmethod objects.
        value = cls.__dict__[name]
        try:
            section.parse_object(name, value)
        except bananadoc.NoDocstring as e:
            # Sometimes it makes sense to define an undocumented
            # __init__, so we'll allow that.
            if name != '__init__':
                raise e

    return True


if enum is not None:
    @bananadoc.parsingfunc
    def parse_enum(parentsect, name, value):
        if not isinstance(value, enum.EnumMeta):
            return False
        if value.__doc__ is None:
            raise bananadoc.NoDocstring(parentsect.fullname, name)
        section = bananadoc.ObjectSection(
            parentsect.fullname, name, value,
            title="enum %s" % name,
            content=inspect.cleandoc(value.__doc__))
        parentsect.subs.append(section)
        return True
