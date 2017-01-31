# BananaDoc

This program is a simple, light-weight alternative to Sphinx using
Markdown instead of reStructuredText.

After adding docstrings and `__all__` lists to everything public, using
this program is really easy:

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

Of course, packages with multiple submodules are fully supported. Each
submodule will be documented to a separate file.
