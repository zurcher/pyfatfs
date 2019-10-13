#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""pyFAT package definition."""

import io
import re

from setuptools import setup, find_packages

try:
    # pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:
    # pip <= 9.0.3
    from pip.req import parse_requirements

def load_requirements(fname):
    reqs = parse_requirements(fname, session="test")
    return [str(ir.req) for ir in reqs]

def _get_attribute(name):
    """Get version information from __init__.py."""
    with io.open('pyfat/__init__.py') as f:
        return re.search(r"{}\s*=\s*'([^']+)'\s*".format(name),
                         f.read()).group(1)

def _get_readme():
    """Get contents of README.rst."""
    with io.open('README.rst') as readme:
        return readme.read()


setup(name='pyfat',
      version=_get_attribute('__version__'),
      description='FAT12/16/32 implementation with VFAT support',
      long_description=_get_readme(),
      author=_get_attribute('__author__'),
      author_email=_get_attribute('__author_email__'),
      license=_get_attribute('__license__'),
      url='https://github.com/Draegerwerk/pyfat',
      packages=find_packages(),
      keywords=['filesystem', 'PyFilesystem2', 'FAT12',
                'FAT16', 'FAT32', 'VFAT', 'LFN'],
      python_requires='~=3.6',
      test_suite='tests',
      install_requires=load_requirements("requirements/install.txt"),
      setup_requires=['pytest-runner'],
      tests_require=load_requirements("requirements/test.txt"),
      entry_points={
          'fs.opener': ['fat = pyfat.PyFatFSOpener:PyFatFSOpener'],
      },
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3 :: Only',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Topic :: Software Development :: Libraries',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Filesystems'],
      )
