"""Set up BananaDoc."""

from setuptools import setup, find_packages

import bananadoc


setup(
    name='bananadoc',
    version=bananadoc.__version__,
    description="collect docstrings to Markdown files",
    url='https://github.com/Akuli/bananadoc/',
    packages=find_packages(),
    entry_points={'console_scripts': ['bananadoc=bananadoc.cmdline:main']},
)
