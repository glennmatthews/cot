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

"""COT - the Common OVF Tool."""

# Install setuptools automatically if not already present
try:
    from setuptools import setup
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup

import os.path
import sys
from distutils.command.build import build
from setuptools.command.bdist_egg import bdist_egg
from setuptools.command.test import test

import versioneer

README_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'README.rst')

install_requires = [
    'argparse',
    'colorlog>=2.5.0',
    'pyvmomi>=5.5.0.2014.1',
    'requests>=2.5.1',
    'verboselogs>=1.0',
]
# shutil.get_terminal_size is standard in 3.3 and later only.
if sys.version_info < (3, 3):
    install_requires.append('backports.shutil_get_terminal_size')

setup_requires = install_requires + ['sphinx>=1.3', 'sphinx_rtd_theme']
tests_require = install_requires + ['unittest2', 'mock']

cmdclass = versioneer.get_cmdclass()


# Ensure that docs are generated whenever build/sdist are run
build.sub_commands.insert(0, ('build_sphinx', None))
cmdclass['sdist'].sub_commands.insert(0, ('build_sphinx', None))


class custom_bdist_egg(bdist_egg):
    """Custom subclass for the 'bdist_egg' command.

    This command is called automatically by 'install', but it doesn't do
    sub_commands, so we have to subclass it instead.
    """

    def run(self):
        """Call build_sphinx then proceed as normal."""
        self.run_command('build_sphinx')
        bdist_egg.run(self)

cmdclass['bdist_egg'] = custom_bdist_egg


class custom_test(test):
    """Custom subclass for the 'test' command."""

    def with_project_on_sys_path(self, func):
        """Make sure docs were built, then proceed as normal."""
        if not os.path.exists(os.path.join(os.path.dirname(__file__),
                                           "COT/docs/man")):
            self.run_command('build_sphinx')
        test.with_project_on_sys_path(self, func)

cmdclass['test'] = custom_test

# Summary of use cases and how they lead to getting the man pages generated:
# setup.py test --> run_command(build_sphinx)
# setup.py sdist --sub_commands--> build_sphinx
# setup.py bdist_egg --> run_command(build_sphinx)
# setup.py bdist_wheel --> run_command(build) --sub_commands--> build_sphinx

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
