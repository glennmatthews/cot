#!/usr/bin/env python
#
# setup.py - installer script for COT package
#
# April 2014, Glenn F. Matthews
# Copyright (c) 2014-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

# Install setuptools automatically if not already present
try:
    from setuptools import setup
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup

import os.path
import sys

import versioneer

versioneer.VCS = 'git'
versioneer.versionfile_source = 'COT/_version.py'
versioneer.versionfile_build = versioneer.versionfile_source    # TODO
versioneer.tag_prefix = 'v'
versioneer.parentdir_prefix = 'cot-'

README_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'README.rst')

install_requires = [
    'argparse',
    'colorlog>=2.5.0',
    'requests>=2.5.1',
    'verboselogs>=1.0',
]
# shutil.get_terminal_size is standard in 3.3 and later only.
if sys.version_info < (3, 3):
    install_requires.append('backports.shutil_get_terminal_size')

setup_requires = ['sphinx>1.2.3']
tests_require = install_requires + ['unittest2']

cmdclass = versioneer.get_cmdclass()

setup(
    # Package description
    name='cot',
    version=versioneer.get_version(),
    author='Glenn Matthews',
    author_email='glenn@e-dad.net',
    url='https://github.com/glennmatthews/cot',
    description='Common OVF Tool',
    long_description=open(README_FILE).read(),
    license='MIT',

    # Requirements
    setup_requires=setup_requires,
    test_suite='unittest2.collector',
    tests_require=tests_require,
    install_requires=install_requires,

    # Package contents
    cmdclass=cmdclass,
    packages=['COT', 'COT.helpers'],
    entry_points={
        'console_scripts': [
            'cot = COT.cli:main',
        ],
    },
    include_package_data=True,

    # PyPI search categories
    classifiers=[
        # Project status
        'Development Status :: 5 - Production/Stable',
        # Target audience
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Emulators',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
        # Licensing
        'License :: OSI Approved :: MIT License',
        # Environment
        'Environment :: Console',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        # Supported versions
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='virtualization ovf ova esxi vmware vcenter',
)
