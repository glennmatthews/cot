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
import subprocess
import sys
from setuptools.command.bdist_egg import bdist_egg
from setuptools import Command

import versioneer
# Extend the "build" command a bit further:
from versioneer import cmd_build

versioneer.VCS = 'git'
versioneer.versionfile_source = 'COT/_version.py'
versioneer.versionfile_build = versioneer.versionfile_source    # TODO
versioneer.tag_prefix = 'v'
versioneer.parentdir_prefix = 'cot-'

README_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'README.rst')
HELPER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "check_and_install_helpers.py")

cmd_class = versioneer.get_cmdclass()

# on_rtd is whether we are on readthedocs.org, this line of code grabbed from
# docs.readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'


class custom_build(cmd_build):
    def run(self):
        try:
            subprocess.check_call([HELPER_SCRIPT, "check"])
        except subprocess.CalledProcessError:
            exit()
        cmd_build.run(self)


# Add a custom 'install_helpers' command:
class custom_install_helpers(Command):
    description = "Install executable helper programs needed by COT"
    user_options = [
        ('force', 'f', 'No prompting for confirmation of installation'),
    ]
    boolean_options = ['force']

    def initialize_options(self):
        self.force = False

    def finalize_options(self):
        pass

    def run(self):
        try:
            if self.force:
                subprocess.check_call([HELPER_SCRIPT, "install", '-f'])
            else:
                subprocess.check_call([HELPER_SCRIPT, "install"])
        except subprocess.CalledProcessError:
            exit('Aborting')


# 'bdist_egg' (called automatically by 'install') to include 'install_helpers'
class custom_bdist_egg(bdist_egg):
    def run(self):
        # Don't bother installing helper tools on readthedocs.org
        if not on_rtd:
            self.run_command('install_helpers')
        bdist_egg.run(self)

cmd_class['build'] = custom_build
cmd_class['install_helpers'] = custom_install_helpers
cmd_class['bdist_egg'] = custom_bdist_egg

install_requires = ['argparse', 'colorlog>=2.5.0', 'verboselogs>=1.0']
# shutil.get_terminal_size is standard in 3.3 and later only.
if sys.version_info < (3, 3):
    install_requires.append('backports.shutil_get_terminal_size')


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
    test_suite='COT.tests',
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
