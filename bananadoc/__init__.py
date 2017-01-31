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

'''Collect docstrings to markdown files.

This module provides a handy command-line interface, and usually you
should use that. You can also import this module and use it that way if
you need to do something that can't be done with the command-line
interface.

Example usage:

```
$ cat hello.py
"""Print Hello World!

This module contains [a function that prints hello world](#hello).
"""

def hello():
    """Print *Hello World!*"""
    print("Hello World!")
$ python3 -m bananadoc hello
Writing documentation...
  hello.py -> docs/reference/README.md

1 module was documented.
$ cat docs/reference/README.md
# hello - print Hello World

This module contains [a function that prints hello world](#hello).

## hello()

Print *Hello World!*

$
```
'''

from bananadoc.parse import (
    NoDocstring, Section, ObjectSection, parsingfunc, modulehook, parse_module)
from bananadoc import defaults  # noqa

__all__ = [
    'defaults', 'cmdline',          # submodules
    'Section', 'ObjectSection',     # classes
    'parsingfunc', 'modulehook',    # hook decorators
    'parse_module',                 # misc functions
    'NoDocstring',                  # exceptions
]
