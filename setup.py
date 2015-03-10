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
import shutil
import sys
from setuptools import Command

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

cmd_class = versioneer.get_cmdclass()


class custom_build_man(Command):

    description = "Build man pages for COT"
    user_options = []

    def __init__(self, dist):
        self.dist = dist
        Command.__init__(self, dist)

    def initialize_options(self):
        from sphinx.setup_command import BuildDoc
        self.build_doc = BuildDoc(self.dist)
        self.build_doc.initialize_options()
        self.build_doc.builder = 'man'

    def finalize_options(self):
        self.build_doc.finalize_options()

    def run(self):
        self.build_doc.run()


class custom_install_man(Command):
    description = "Install man pages for COT"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        src = os.path.join(os.path.dirname(__file__), 'build', 'sphinx', 'man')
        if not os.path.exists(src):
            raise RuntimeError("need to run 'setup.py build_sphinx -b man'")
        dest = "/usr/share/man/man8"
        for f in os.listdir(src):
            # Which man section does this belong in?
            section = os.path.splitext(f)[1][1:]
            dest = "/usr/share/man/man{0}/".format(section)
            if not os.path.exists(dest):
                os.makedirs(dest)
            print("Copying {0} to {1}".format(f, dest))
            shutil.copy(os.path.join(src, f), dest)

cmd_class['build_man'] = custom_build_man
cmd_class['install_man'] = custom_install_man

setup(
    name='cot',
    version=versioneer.get_version(),
    cmdclass=cmd_class,
    author='Glenn Matthews',
    author_email='glenn@e-dad.net',
    packages=['COT', 'COT.helpers'],
    entry_points={
        'console_scripts': [
            'cot = COT.cli:main',
        ],
    },
    url='https://github.com/glennmatthews/cot',
    license='MIT',
    description='Common OVF Tool',
    long_description=open(README_FILE).read(),
    setup_requires=['sphinx>1.2.3'],
    test_suite='unittest2.collector',
    tests_require=install_requires + ['unittest2'],
    install_requires=install_requires,
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
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='virtualization ovf ova esxi vmware vcenter',
)
