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

"""The parsing functions."""

import functools
import importlib
import inspect
import os
import types

try:
    import enum
except ImportError:
    # Running on Python 3.3 without enum34, but we don't need to warn
    # about this because the modules we are documenting can't contain
    # enums.
    enum = None


class NoDocstring(Exception):
    """This is raised when a docstring is missing."""

    def __init__(self, *problem):
        # Calling super().__init__() is not needed. This is documented
        # behaviour, not an implementation detail.
        self._problem = '.'.join(problem)

    def __str__(self):
        return "%r doesn't have a docstring" % self._problem


_parsingfuncs = []


def parsingfunc(parsingfunc):
    """Add a function that converts a documentable object to a Section.

    This is supposed to be used as a decorator. For example, like this:

    ```python
    @parsingfunc
    def parse_string(parentsection, name, value):
        if not isinstance(value, str):
            return False    # not processed
        sub = bananadoc.ObjectSection(
            parent.fullname, name, value,
            title="The '%s' string" % name,
            content="The value of this string is `%r`." % value)
        parentsection.subs.append(sub)
        return True     # processed
    ```

    This parsing function would make strings like `hello = 'world'` look
    like this:

    ```
    ## The 'hello' string

    The value of this string is 'world'.
    ```

    The parsing function should return True if it documented the value
    and False if it can't document it. It should take these positional
    arguments:
    - *section:* A [Section](#section) object. The function should set
      its *title* and *content* attributes.
    - *value:* The value that is being documented.
    """
    _parsingfuncs.append(parsingfunc)
    return parsingfunc


class Section:
    """A section with a title and content.

    When written to a Markdown file, each section starts with a title
    and ends with the beginning of another section. The sections may
    also contain subs with smaller titles.

    Section objects have these attributes:

    - *title:* The title of this section, without `#` characters.
    - *content:* The content of this section as a string without a
      title. Leading and trailing newlines are ignored.
    - *subs:* A list of other Section objects inside this section.
    """

    def __init__(self, title=None, content=None):
        """Initialize the Section."""
        self.title = title
        self.content = content
        self.subs = []

    def __repr__(self):
        if len(self.subs) == 1:
            subs = "1 subsection"
        else:
            subs = "%d subsections" % len(self.subs)
        return "<%s %r, %s>" % (type(self).__name__, self.title, subs)

    def walk_subs(self):
        """Iterate over the subsections recursively.

        This does not include the initial subsection.
        """
        for sub in self.subs:
            yield sub
            yield from sub.walk_subs()

    def dump(self, stream, titlelevel=1):
        """Write the documentation to *stream*."""
        assert self.title is not None, "title of %r wasn't set" % self
        assert self.content is not None, "content of %r wasn't set" % self
        print('#' * titlelevel, self.title, end='\n\n', file=stream)
        print(self.content.strip('\n'), end='\n\n', file=stream)
        for sub in self.subs:
            sub.dump(stream, titlelevel+1)


class ObjectSection(Section):
    """An object that represents a Python object's documentation.

    In addition to [Section](#section) attributes, ObjectSections also
    have these attributes:

    - *location:* A modulename-like string that points to the object
      that this section represents. For example, if there's a class
      `SomeClass` in `some.module` and this section represents
      `SomeClass.method()`, the *location* value is
      `some.module.SomeClass`. This is None if the section is the top
      level module that everything else is in.
    - *name:* The name in *location* that this section represents. This
      would be `method` in the previous example.
    - *value:* The value that is documented.
    """

    def __init__(self, location, name, value, **kwargs):
        """Initialize the ObjectSection.

        `**kwargs` are passed to [Section](#section)'s `__init__`.
        """
        super().__init__(**kwargs)
        self.location = location
        self.name = name
        self.value = value

    @property
    def fullname(self):
        """This is *location* and *name* joined with a dot.

        If this is the top level module and *location* is None, this is
        just the *name*.
        """
        if self.location is None:
            return self.name
        return self.location + '.' + self.name

    def parse_object(self, name, obj):
        """Try to parse an object using parsing functions."""
        # We need to reverse because we want to use newly added dump
        # functions first.
        for parsingfunc in reversed(_parsingfuncs):
            if parsingfunc(self, name, obj):
                # It did it.
                return
        # The data parsing function should be able to parse anything.
        assert False, ("the data parsing function didn't catch %s.%s"
                       % (self.fullname, name))


# This will contain functions that are called on the top level Section
# before dumping it.
_modulehooks = []


def modulehook(func):
    """Add a module parsing hook function.

    See [parse_module](#parse-module) for more info.
    """
    _modulehooks.append(func)
    return func


def _module_sorting_key(module, name):
    """A key function for sorting a name list of a module.

    This prioritizes everything like this:
      1. classes
      2. functions
      3. exceptions
      4. other data
    """
    value = getattr(module, name)
    if isinstance(value, type):
        if issubclass(value, Exception):
            return 3, name
        return 1, name
    if isinstance(value, types.FunctionType):
        return 2, name
    return 4, name


def _clean_summary(line):
    firstword, space, rest = line.partition(' ')
    if firstword[0].isupper() and firstword[1:].islower():
        # The first word is Capitalized, we can lowercase it without
        # screwing things up.
        firstword = firstword.lower()
    return (firstword + space + rest).rstrip('.?!')


def _import_submodules(package):
    for path in package.__path__:
        for name, ext in map(os.path.splitext, os.listdir(path)):
            if (ext == '.py'
                    and name.isidentifier()
                    and not name.startswith('_')):
                # public Python module with a valid name
                importlib.import_module(package.__name__ + '.' + name)


def parse_module(modulename):
    """Create an [ObjectSection](#objectsection) of a module.

    Each hook function added with [modulehook](#modulehook) is called on
    the section before returning it.

    This does not document submodules, so this returns the section and a
    list of public submodule names that were not documented.
    """
    module = importlib.import_module(modulename)
    if module.__doc__ is None:
        raise NoDocstring(modulename)
    its_a_package = hasattr(module, '__path__')

    try:
        all_list = module.__all__
    except AttributeError:
        if its_a_package:
            # We need to import all submodules. Just importing them
            # attaches them to the module object, so the dir() will find
            # them.
            _import_submodules(module)
        all_list = []
        for name in dir(module):
            if not name.startswith('_'):
                all_list.append(name)
        key = functools.partial(_module_sorting_key, module)
        all_list.sort(key=key)

    doc = inspect.cleandoc(module.__doc__)
    summary, junk, description = doc.partition('\n')
    title = modulename
    if summary:
        title += " - "
        title += _clean_summary(summary)

    mainsection = ObjectSection(None, modulename, module,
                                title=title, content=description)

    submodules = []
    for name in all_list:
        if its_a_package:
            try:
                submodulename = modulename + '.' + name
                importlib.import_module(submodulename)
                # It's a submodule.
                submodules.append(submodulename)
                continue
            except ImportError:
                # It's a variable, keep going normally.
                pass
        mainsection.parse_object(name, getattr(module, name))

    for hook in _modulehooks:
        hook(mainsection)

    return mainsection, submodules
