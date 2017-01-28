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

"""Collect docstrings to markdown files.

This module provides a handy command-line interface, and usually you
should use that. You can also import this module and use it that way if
you need to do something that can't be done with the command-line
interface.

The [dump](#dump) function extracts a module's documentation into a
file, and other functions in this module are meant to be used for
customizing the dumping process.

When the command-line interface or the [dump](#dump) function is ran,
this module extracts docstrings from a Python modules and turns them
into markdown. First the module is imported, a [Writer](#writer) object
is created and the module's docstring is written to the writer. Then the
[dump_object](#dump-object) function is called once for each variable
named in the module's `__all__` list.
"""

import sys
assert sys.version_info >= (3, 3), "Python 3.3 is required"  # noqa

import argparse
import collections
import contextlib
import importlib
import inspect
import operator
import os
import shutil
# sys is already imported.
import textwrap

try:
    import enum
except ImportError:
    # Running on Python 3.3 without enum34, but we don't need to warn
    # about this because the modules we are documenting can't contain
    # enums.
    enum = None


__version__ = '1.0'
__all__ = [
    'dump', 'dump_object', 'add_dumpfunc', 'Writer',
    'NotDocumented', 'NoDocstring', 'NoAll',
    'main']


class NotDocumented(Exception):
    """This is raised when a part of a public interface is not documented.

    Usually it's best to raise a subclass of this exception instead of
    raising this directly, but catching NotDocumented may be useful.
    """

    def __str__(self):
        return '.'.join(self.args)


class NoDocstring(NotDocumented):
    """This is raised when a docstring is missing."""

    def __str__(self):
        return "%s has no docstring" % super().__str__()


class NoAll(NotDocumented):
    """This is raised when the `__all__` list is missing."""

    def __str__(self):
        return "%s has no __all__ list" % super().__str__()


class Writer:
    """An object for writing markdown strings to a file object easily.

    The Writers also add titles. When the writing is done, each function 
    in the `finalizers` list will be called with the writer as the only 
    argument.
    """

    def __init__(self, module, stream):
        self.module = module
        self.stream = stream
        self.finalizers = []
        self._titlelevel = 1

    def __enter__(self):
        return self

    def __exit__(self, *error):
        for func in self.finalizers:
            func(self)

    def write(self, *args, end='\n\n', **kwargs):
        r"""Write a message to `self.stream`.

        The arguments are like for `print()`, but *end* defaults to
        '\n\n' and *file* is always `self.stream`.
        """
        print(*args, end=end, file=self.stream, **kwargs)

    @contextlib.contextmanager
    def section(self, title):
        """Add a section with a title.

        The sections can be nested. For example, this...

        ```py
        with some_writer.section("hello"):
            some_writer.write("there")
        ```

        ...writes this:

        ```
        # hello

        there
        ```

        If sections are nested, more `#` characters will be used in
        front of the titles.
        """
        self.write('#' * self._titlelevel, title)
        self._titlelevel += 1
        try:
            yield
        finally:
            self._titlelevel -= 1


_dumpfuncs = []


def add_dumpfunc(dumpfunc):
    """Add a function for dumping an object.

    This is supposed to be used as a decorator. For example, like this:

    ```py
    @add_dumpfunc
    def dump_string(writer, where, name, value):
        if not isinstance(value, str):
            return False    # not processed
        writer.write(
            "There's a %s variable that points to the string %r."
            % (name, the_string))
        return True     # processed
    ```

    The dumping function should return True if it did something, and
    take these positional arguments:
    - *writer:* A [Writer](#writer) object.
    - *where:* A modulename-like string that points to where the value
        came from. For example, 'some.module' or 'some.module.SomeClass'.
    - *name:* The value's variable name in the location specified with
        *where*.
    - *value:* The value that will be documented.
    """
    _dumpfuncs.append(dumpfunc)
    return dumpfunc


def dump_object(writer, where, name, obj):
    """Dump *obj* to *writer*.

    The [dump](#dump) function uses this, and you can use this in custom
    dumping functions for things that contain other things that also
    need dumping. For example, the default class dumping function uses
    this function to dump information about methods and other class
    attributes.

    See [add_dumpfunc](add_dumpfunc) if you want to customize what this
    method does.
    """
    # We need to reverse because we want to use newly added dump
    # functions first.
    for dumpfunc in reversed(_dumpfuncs):
        if dumpfunc(writer, where, name, obj):
            # It did it.
            return
    # The data dumpfunc should be able to document anything.
    assert False, "the data dumpfunc should have caught %r" % (obj,)


@add_dumpfunc
def _dump_data(writer, where, name, value):
    writer.write(name, "=", repr(value))
    return True


@add_dumpfunc
def _dump_function(writer, where, name, func):
    if not inspect.isfunction(func):
        return False
    title = name + str(inspect.signature(func))  # e.g. thing(a, b, c)
    if func.__doc__ is None:
        raise NoDocstring(where, name)
    with writer.section(title):
        writer.write(inspect.cleandoc(func.__doc__))
    return True


@add_dumpfunc
def _dump_property(writer, where, name, prop):
    if not isinstance(prop, property):
        return False
    if prop.__doc__ is None:
        raise NoDocstring(where, name)
    with writer.section("The %s property" % name):
        writer.write(inspect.cleandoc(prop.__doc__))
    return True


@add_dumpfunc
def _dump_class(writer, where, name, cls):
    if not isinstance(cls, type):
        # It's not a class.
        return False
    if enum is not None:
        assert not isinstance(cls, enum.EnumMeta), \
               "the enum dumper didn't work: %r" % (cls,)
    if cls.__doc__ is None:
        raise NoDocstring(where, name)

    bases = []
    for baseclass in cls.__bases__:
        if baseclass is object or baseclass.__name__.startswith('_'):
            # An implementation detail.
            pass
        if baseclass.__module__ in {where, 'builtins'}:
            bases.append(baseclass.__name__)
        else:
            bases.append(baseclass.__module__ + '.' + baseclass.__name__)

    displayname = name
    if bases:
        displayname += '(%s)' % ', '.join(bases)

    with writer.section("class %s" % displayname):
        if cls.__doc__ is not None:
            writer.write(inspect.cleandoc(cls.__doc__))

        # We don't want to document anything that comes from the bases,
        # so we need to use the __dict__. This way we also get the real
        # classmethods and staticmethods, not whatever their __get__
        # returns.
        items = list(cls.__dict__.items())
        items.sort(key=operator.itemgetter(0))  # Sort by names.
        for attribute, value in items:
            if attribute.startswith('_'):
                # include only if _bananadoc_ignore is False
                if getattr(value, '_bananadoc_ignore', True):
                    continue
            dump_object(writer, where + '.' + name, attribute, value)

    return True


if enum is not None:
    @add_dumpfunc
    def _dump_enum(writer, where, name, enumclass):
        if not isinstance(enumclass, enum.EnumMeta):
            return False

        with writer.section("enum %s" % name):
            if enumclass.__doc__ is None:
                lines = ["%s contains these members:" % name]
                # Iterating over the enum does not include aliases.
                for name in enumclass.__members__:
                    lines.append("- *%s*" % name)
                writer.write('\n'.join(lines))
            else:
                writer.write(inspect.cleandoc(enumclass.__doc__))
        return True


def _clean_summary(line):
    firstword, space, rest = line.partition(' ')
    if firstword[0].isupper() and firstword[1:].islower():
        # The first word is Capitalized.
        firstword = firstword.lower()
    return (firstword + space + rest).rstrip('.')


def dump(modulename, module=None, stream=None):
    """Dump documentation of *modulename* to *stream*.

    This is an easy and high-level way to use the rest of this module.

    The *stream* defaults to `sys.stdout` and the *module* is imported
    if needed. No submodules are documented, but the names of
    undocumented submodules are returned as a list.
    """
    if stream is None:
        stream = sys.stdout

    if module is None:
        module = importlib.import_module(modulename)
    if module.__doc__ is None:
        raise NoDocstring(modulename)
    if not hasattr(module, '__all__'):
        raise NoAll(modulename)
    its_a_package = hasattr(module, '__path__')

    doc = inspect.cleandoc(module.__doc__)
    summary, junk, description = doc.partition('\n')
    title = modulename
    if summary:
        title += " - "
        title += _clean_summary(summary)

    with Writer(module, stream) as writer:
        with writer.section(title):
            writer.write(description.lstrip('\n'))
            submods = []
            for name in module.__all__:
                if its_a_package:
                    try:
                        importlib.import_module(modulename + '.' + name)
                        # It's a submodule.
                        submods.append(modulename + '.' + name)
                        continue
                    except ImportError:
                        # It's a variable, just keep going normally.
                        pass
                value = getattr(module, name)
                dump_object(writer, modulename, name, value)

    return submods


def _mkdir_open(path, *args, **kwargs):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    return open(path, *args, **kwargs)


# As you can see, I like apt-get's command-line interface... :)

def _yesno(prompt, default=True):
    if default:
        prompt += ' [Y/n] '
    else:
        prompt += ' [y/N] '
    while True:
        result = input(prompt).upper().strip()
        if result == 'Y':
            return True
        if result == 'N':
            return False
        if not result:
            return default


def _table(title, stringlist):
    """Print a list of strings in an apt-get style table."""
    print(title)
    for line in textwrap.wrap(' '.join(sorted(stringlist))):
        print(" ", line)


def main():
    """Run the command-line interface.

    This uses `sys.argv` and may use `sys.exit`.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'module', help="name of the module that will be documented")
    parser.add_argument(
        '--no-submodules', dest='document_submodules', action='store_false',
        help="don't document submodules recursively")
    parser.add_argument(
        '-o', '--outdir', default=os.path.join('docs', 'reference'),
        help=("write output files into this directory, "
              "defaults to %(default)s"))
    parser.add_argument(
        '-q', '--quiet', action='store_true', help="produce less output")
    parser.add_argument(
        '-y', '--yes', action='store_true',
        help="assume yes instead of asking questions")
    args = parser.parse_args()

    # The current working directory needs to be the first thing on
    # sys.path because the documented module and the rc file come from
    # there.
    if not os.path.samefile(sys.path[0], os.curdir):
        sys.path.insert(0, os.curdir)

    # This needs to be a local import because unlike most other things,
    # the rc file is supposed to have side effects when importing.
    try:
        import bananadocrc
    except ImportError:
        pass

    # We need to check for this here because .stuff would later turn
    # into /stuff.
    if not all(args.module.split('.')):
        parser.error("invalid module name %r" % args.module)

    if os.path.exists(args.outdir):
        if not args.yes:
            # ask about removing it
            if not _yesno("'%s' exists. Remove it?" % args.outdir, False):
                print("Interrupt.", file=sys.stderr)
                sys.exit(1)
        if os.path.isdir(args.outdir):
            shutil.rmtree(args.outdir)
        else:
            os.remove(args.outdir)

    if not args.quiet:
        print("Writing documentation to '%s'..." % args.outdir)
    documented = []
    undocumented = []
    module_queue = collections.deque([args.module])
    while module_queue:
        modname = module_queue.popleft()
        module = importlib.import_module(modname)
        if modname == args.module:
            # 'fooproject' -> 'OUTDIR/README.md'
            outfile = os.path.join(args.outdir, 'README.md')
        elif hasattr(module, '__path__'):
            # It's a package.
            # 'fooproject.bar.baz' -> 'OUTDIR/bar/baz/README.md'
            parts = modname.split('.')[1:] + ['README.md']
            outfile = os.path.join(args.outdir, *parts)
        else:
            # 'fooproject.bar.baz' -> 'OUTDIR/bar/baz.md'
            parts = modname.split('.')[1:]
            outfile = os.path.join(args.outdir, *parts) + '.md'
        if not args.quiet:
            print(('%s -> %s' % (modname, outfile)).ljust(70), end='\r')
        try:
            with _mkdir_open(outfile, 'w') as f:
                submodules = dump(modname, module, f)
                if args.document_submodules:
                    module_queue.extend(submodules)
                else:
                    undocumented.extend(submodules)
            documented.append(modname)
        except Exception as e:
            # avoid ending up with the traceback on top of the current 
            # module name
            if not args.quiet:
                print()
            raise e

    if not args.quiet:
        # clear the last line from \r tricks and leave it empty
        print(" " * 70)

        if len(documented) == 1:
            print("1 module was documented.")
        else:
            print(len(documented), "modules were documented.")

        if undocumented:
            if len(undocumented) == 1:
                _table("This submodule was NOT documented:", undocumented)
            else:
                _table("These submodules were NOT documented:", undocumented)


if __name__ == '__main__':
    main()
