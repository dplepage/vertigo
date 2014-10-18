#!/usr/bin/env python

from distutils.core import setup

setup(
    name='vertigo',
    version='0.1.2',
    license='BSD',
    author="Daniel Lepage",
    author_email="dplepage@gmail.com",
    packages=['vertigo',],
    long_description="""
=========================================
 Vertigo: Some really simple graph tools
=========================================

Vertigo is a small collection of classes and functions for building and working
with graphs with labeled edges. This is useful because dictionaries are just
graphs with labeled edges, and objects in Python are just dictionaries, so
really this applies to pretty much all objects.

See README.rst for more info

""",
    url='https://github.com/dplepage/vertigo',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ]
)