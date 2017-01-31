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

"""The command-line interface.

Invoking this module like `python3 -m bananadoc.cmdline` does nothing,
but `python3 -m bananadoc` runs this module.
"""

import argparse
import collections
import importlib
import os
import shutil
import sys
import textwrap

import bananadoc


__all__ = ['main']


def mkdir_open(path, *args, **kwargs):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    return open(path, *args, **kwargs)


def nice_path(absolute):
    relative = os.path.relpath(absolute, os.getcwd())
    if relative.startswith(os.pardir + os.sep):
        # /some/path is better than ../../some/path
        return absolute
    return relative


# As you can see, I like apt-get's command-line interface... :)

def yesno(prompt, default=True):
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


def table(strings):
    """Print an iterable of strings in an apt-get style table."""
    for line in textwrap.wrap(' '.join(sorted(strings))):
        print(" ", line)


_desc = "Generate Markdown documentation from Python docstrings."


def main():
    """Run the command-line interface.

    This uses `sys.argv` and may use `sys.exit`.
    """
    parser = argparse.ArgumentParser(description=_desc)
    parser.add_argument(
        'module', help="name of the module that will be documented")
    parser.add_argument(
        '-q', '--quiet', action='store_true', help="produce less output")
    parser.add_argument(
        '-y', '--yes', action='store_true',
        help="assume yes instead of asking questions")
    parser.add_argument(
        '--no-submodules', action='store_true',
        help="don't document submodules recursively")
    parser.add_argument(
        '-o', '--outdir', default=os.path.join('docs', 'reference'),
        help="write output files here, defaults to %(default)s")

    args = parser.parse_args()

    # The current working directory needs to be the first thing on
    # sys.path because the documented module and the rc file come from
    # there.
    try:
        if not os.path.samefile(sys.path[0], os.curdir):
            sys.path.insert(0, os.getcwd())
    except FileNotFoundError:
        # sys.path[0] doesn't exist.
        sys.path.insert(0, os.getcwd())

    # We need to check for this here because .stuff would later turn
    # into /stuff.
    if not all(args.module.split('.')):
        parser.error("invalid module name %r" % args.module)

    if os.path.exists(args.outdir):
        # if --yes was given, leave it alone which is the default
        if not args.yes:
            if yesno("'%s' exists. Remove it?" % args.outdir, False):
                if os.path.isdir(args.outdir):
                    shutil.rmtree(args.outdir)
                else:
                    os.remove(args.outdir)

    if not args.quiet:
        print("Writing documentation...")

    documented = 0
    undocumented = []
    module_queue = collections.deque([args.module])
    while module_queue:
        modname = module_queue.popleft()
        module = importlib.import_module(modname)
        if modname == args.module:
            # 'fooproject' -> 'outdir/README.md'
            outfile = os.path.join(args.outdir, 'README.md')
        elif hasattr(module, '__path__'):
            # It's a package.
            # 'fooproject.bar.baz' -> 'outdir/bar/baz/README.md'
            parts = [args.outdir] + modname.split('.')[1:] + ['README.md']
            outfile = os.path.join(*parts)
        else:
            # 'fooproject.bar.baz' -> 'outdir/bar/baz.md'
            parts = modname.split('.')[1:]
            outfile = os.path.join(args.outdir, *parts) + '.md'
        if not args.quiet:
            print(' ', nice_path(module.__file__), '->', outfile)

        mainsection, subs = bananadoc.parse_module(modname)
        if not args.no_submodules:
            module_queue.extend(subs)
        else:
            undocumented.extend(subs)
        with mkdir_open(outfile, 'w') as f:
            mainsection.dump(f)
        documented += 1

    if not args.quiet:
        print()
        if documented == 1:
            print("1 module was documented.")
        else:
            print(documented, "modules were documented.")
        if undocumented:
            if len(undocumented) == 1:
                print("This submodule was NOT documented:")
            else:
                print("These submodules were NOT documented:")
            table(undocumented)
