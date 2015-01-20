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

import versioneer

versioneer.VCS = 'git'
versioneer.versionfile_source = 'COT/_version.py'
versioneer.versionfile_build = versioneer.versionfile_source # TODO
versioneer.tag_prefix = 'v'
versioneer.parentdir_prefix = 'cot-'

import os.path
import subprocess
from setuptools.command.bdist_egg import bdist_egg
from setuptools import Command

README_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'README.md')
HELPER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "check_and_install_helpers.py")

cmd_class = versioneer.get_cmdclass()

# Extend the "build" command a bit further:
from versioneer import cmd_build
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
        self.run_command('install_helpers')
        bdist_egg.run(self)

cmd_class['build'] = custom_build
cmd_class['install_helpers'] = custom_install_helpers
cmd_class['bdist_egg'] = custom_bdist_egg

setup(
    name='common-ovf-tool',
    version=versioneer.get_version(),
    cmdclass=cmd_class,
    author='Glenn Matthews',
    author_email='glenn@e-dad.net',
    packages=['COT'],
    entry_points = {
        'console_scripts': [
            'cot = COT.cli:main',
        ],
    },
    url='https://github.com/glennmatthews/cot',
    license=open('LICENSE.txt').read(),
    description='Common OVF Tool',
    long_description=open(README_FILE).read(),
    test_suite='COT.tests',
    install_requires=['argparse', 'coloredlogs>=0.8', 'verboselogs>=1.0'],
)
