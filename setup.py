#!/usr/bin/env python
#
# setup.py - installer script for COT package
#
# April 2014, Glenn F. Matthews
# Copyright (c) 2014-2017 the COT project developers.
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

from __future__ import print_function

# Install setuptools automatically if not already present
try:
    from setuptools import setup
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup

import os.path
import re
from distutils.command.build import build
import versioneer
from setuptools.command.bdist_egg import bdist_egg

# At present setuptools has no way to resolve build-time dependencies.
# Sphinx is needed to regenerate the COT man pages at build time,
# but is not actually a setup requirement or an install requirement.
# See also:
#     https://github.com/pypa/pip/issues/2381

# Also, to reduce noise in the repository, we only auto-update the man pages
# if we're working in a release candidate, hotfix, or master branch
GIT_HEAD = os.path.join(os.path.dirname(__file__), ".git", "HEAD")
rebuild_manpages = False
if os.path.exists(GIT_HEAD):
    head_data = open(GIT_HEAD).read()
    match = re.match(r"ref: refs/heads/(.*)", head_data)
    if match:
        branch = match.group(1)
        print("Current branch is {0}".format(branch))
        if any(branch.startswith(pfx) for pfx in ['release',
                                                  'hotfix',
                                                  'master']):
            rebuild_manpages = True
        else:
            print("COT manual pages will not be automatically rebuilt.")
            print("You may run '{0} build_man' to rebuild them manually."
                  .format(os.path.basename(__file__)))

try:
    from sphinx.setup_command import BuildDoc

    class BuildMan(BuildDoc):
        """Command to (re)build man pages using Sphinx."""

        def initialize_options(self):
            """Default to manpage builder."""
            BuildDoc.initialize_options(self)
            self.builder = 'man'

except ImportError:
    from distutils.cmd import Command
    import time

    class BuildMan(Command):
        """No-op."""

        def initialize_options(self):
            """No-op."""
            self.config_dir = self.build_dir = None

        user_options = []
        finalize_options = initialize_options

        def run(self):
            """Print a warning message and return."""
            print("\033[1;31m")
            print("WARNING: Sphinx is not installed.")
            print("         As a result, COT cannot update its man pages.")
            print("         If you are building for a release, please:")
            print("             pip install -r requirements.txt")
            print("             pip install 'sphinx>=1.5' sphinx_rtd_theme")
            print("         and then rerun this command.")
            print("\033[0;0m")
            # Give the user time to take notice
            time.sleep(10)
            print("Continuing...")

README_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'README.rst')

install_requires = [
    'argparse',
    'colorlog>=2.5.0',
    'pyvmomi>=5.5.0.2014.1',
    'requests>=2.5.1',
    'verboselogs>=1.6',

    # http://docs.python-requests.org/en/latest/community/
    #      faq/#what-are-hostname-doesn-t-match-errors
    # COT tends to run into this issue when downloading the VMDKtool source
    'pyOpenSSL; python_version < "2.7.9"',
    'ndg-httpsclient; python_version < "2.7.9"',
    # shutil.get_terminal_size is standard in 3.3 and later only.
    'backports.shutil_get_terminal_size; python_version < "3.3"',
    # enum module is standard in Python 3.4 and later, else use enum34
    'enum34; python_version < "3.4"',
]

tests_require = install_requires + ['unittest2', 'mock']

extras_require = {
    'tab-completion': ['argcomplete>=1.3.0'],
}

cmdclass = versioneer.get_cmdclass()

cmdclass['build_man'] = BuildMan

if rebuild_manpages:
    class BDistEgg(bdist_egg):
        """Custom subclass for the 'bdist_egg' command.

        This command is called automatically by 'install', but it doesn't do
        sub_commands, so we have to subclass it instead.
        """

        def run(self):
            """Call build_man then proceed as normal."""
            self.run_command('build_man')
            bdist_egg.run(self)

    # Ensure that man pages are regenerated whenever build/sdist are run
    # setup.py sdist --sub_commands--> build_man
    cmdclass['sdist'].sub_commands.insert(0, ('build_man', None))
    # setup.py bdist_egg --> run_command(build_man)
    cmdclass['bdist_egg'] = BDistEgg
    # setup.py bdist_wheel --> run_command(build) --sub_commands--> build_man
    build.sub_commands.insert(0, ('build_man', None))

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
    test_suite='unittest2.collector',
    tests_require=tests_require,
    install_requires=install_requires,
    extras_require=extras_require,

    # Package contents
    cmdclass=cmdclass,
    packages=[
        'COT',
        'COT.commands',
        'COT.disks',
        'COT.helpers',
        'COT.platforms',
        'COT.ui',
        'COT.vm_description',
        'COT.vm_description.ovf',
    ],
    package_data={
        'COT': ['docs/man/*'],
    },
    entry_points={
        'console_scripts': [
            'cot = COT.ui.cli:main',
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
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    keywords='virtualization ovf ova esxi vmware vcenter',
)
