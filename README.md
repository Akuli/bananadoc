# BananaDoc

This program is a simple, light-weight alternative to Sphinx using
Markdown instead of reStructuredText.

After adding docstrings and `__all__` lists to everything public, using
this program is really easy:

```
$ tree my_project
my_project
├── __init__.py
└── submodule.py

0 directories, 2 files
$ bananadoc my_project
Writing documentation to 'docs/reference'...

2 modules were documented.
$ tree docs/
docs/
└── reference/
    ├── README.md
    └── submodule.md

1 directory, 2 files
$
```
