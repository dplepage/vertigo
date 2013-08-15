#!/usr/bin/env python

from distutils.core import setup

setup(
    name='vertigo',
    version='0.1.1',
    license='BSD',
    author="Daniel Lepage",
    author_email="dplepage@gmail.com",
    packages=['vertigo',],
    long_description=open('README.rst').read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 2",
    ]
)