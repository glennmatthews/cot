#!/usr/bin/env python
#
# fatdisk.py - Helper for 'fatdisk'
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2013-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Give COT access to ``fatdisk`` for creating and updating FAT32 file systems.

http://github.com/goblinhack/fatdisk
"""

import logging
import os
import os.path
import platform

from COT.helpers.helper import Helper, helpers, check_call, helper_select

logger = logging.getLogger(__name__)


class FatDisk(Helper):
    """Wrapper for ``fatdisk`` (http://github.com/goblinhack/fatdisk)."""

    def __init__(self):
        """Initializer."""
        super(FatDisk, self).__init__(
            "fatdisk",
            info_uri="http://github.com/goblinhack/fatdisk",
            version_regexp="version ([0-9.]+)")

    _provider_package = {
        'brew': ['glennmatthews/fatdisk/fatdisk', '--devel'],
        'port': 'fatdisk',
    }

    @property
    def installable(self):
        """Whether COT is capable of installing this program on this system."""
        return bool(helpers['brew'] or helpers['port'] or
                    (platform.system() == 'Linux' and
                     (helpers['make'] or helpers['make'].installable) and
                     (helpers['clang'] or helpers['gcc'] or
                      helpers['g++'] or helpers['gcc'].installable)))

    def _install(self):
        """Install ``fatdisk``."""
        try:
            super(FatDisk, self)._install()
            return
        except NotImplementedError:
            # We have an alternative install method available for Linux,
            # below - but if not Linux, you're out of luck!
            if platform.system() != 'Linux':
                raise

        # Fatdisk installation requires make
        helpers['make'].install()

        # Fatdisk build requires clang or gcc or g++,
        # but COT doesn't care which one we have.
        helper_select(['clang', 'gcc', 'g++'])

        with self.download_and_expand_tgz(
                'https://github.com/goblinhack/'
                'fatdisk/archive/v1.0.0-beta.tar.gz') as d:
            new_d = os.path.join(d, 'fatdisk-1.0.0-beta')
            logger.info("Compiling 'fatdisk'")
            check_call(['./RUNME'], cwd=new_d)
            destdir = os.getenv('DESTDIR', '')
            prefix = os.getenv('PREFIX', '/usr/local')
            # os.path.join doesn't like absolute paths in the middle
            if destdir != '':
                prefix = prefix.lstrip(os.sep)
            destination = os.path.join(destdir, prefix, 'bin')
            logger.info("Compilation complete, installing to " +
                        destination)
            self.mkdir(destination)
            self.cp(os.path.join(new_d, 'fatdisk'), destination)
