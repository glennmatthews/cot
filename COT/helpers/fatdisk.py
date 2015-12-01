#!/usr/bin/env python
#
# fatdisk.py - Helper for 'fatdisk'
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2013-2015 the COT project developers.
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
import shutil

from .helper import Helper

logger = logging.getLogger(__name__)


class FatDisk(Helper):
    """Helper provider for ``fatdisk`` (http://github.com/goblinhack/fatdisk).

    **Methods**

    .. autosummary::
      :nosignatures:

      install_helper
      create_raw_image
    """

    def __init__(self):
        """Initializer."""
        super(FatDisk, self).__init__("fatdisk",
                                      version_regexp="version ([0-9.]+)")

    def install_helper(self):
        """Install ``fatdisk``."""
        if self.path:
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.name, self.path))
            return
        logger.info("Installing 'fatdisk'...")
        if Helper.port_install('fatdisk'):
            pass
        elif platform.system() == 'Linux':
            # Fatdisk installation requires make
            if not self.find_executable('make'):
                logger.info("fatdisk requires 'make'... installing 'make'")
                if not (Helper.apt_install('make') or
                        Helper.yum_install('make')):
                    raise NotImplementedError("Not sure how to install 'make'")
            # Fatdisk requires clang or gcc or g++
            if not (self.find_executable('clang') or
                    self.find_executable('gcc') or
                    self.find_executable('g++')):
                logger.info(
                    "fatdisk requires a C compiler... installing 'gcc'")
                if not (Helper.apt_install('gcc') or
                        Helper.yum_install('gcc')):
                    raise NotImplementedError(
                        "Not sure how to install a C compiler")
            with self.download_and_expand(
                    'https://github.com/goblinhack/'
                    'fatdisk/archive/v1.0.0-beta.tar.gz') as d:
                new_d = os.path.join(d, 'fatdisk-1.0.0-beta')
                logger.info("Compiling 'fatdisk'")
                self._check_call(['./RUNME'], cwd=new_d)
                destdir = os.getenv('DESTDIR', '')
                prefix = os.getenv('PREFIX', '/usr/local')
                # os.path.join doesn't like absolute paths in the middle
                if destdir != '':
                    prefix = prefix.lstrip(os.sep)
                destination = os.path.join(destdir, prefix, 'bin')
                logger.info("Compilation complete, installing to " +
                            destination)
                self.make_install_dir(destination)
                try:
                    shutil.copy(os.path.join(new_d, 'fatdisk'), destination)
                except OSError:
                    logger.verbose('Installation error, trying sudo')
                    self._check_call(['sudo', 'cp', 'fatdisk', destination],
                                     cwd=new_d)
        else:
            raise NotImplementedError(
                "Not sure how to install 'fatdisk'.\n"
                "See https://github.com/goblinhack/fatdisk")
        logger.info("Successfully installed 'fatdisk'")

    def create_raw_image(self, file_path, contents, capacity=None):
        """Create a new FAT32-formatted raw image at the requested location.

        :param str file_path: Desired location of new disk image
        :param list contents: List of file paths to package into the created
          image.
        :param capacity: (optional) Disk capacity. A string like '16M' or '1G'.
        """
        if not capacity:
            # What size disk do we need to contain the requested file(s)?
            capacity = 0
            for content_file in contents:
                capacity += os.path.getsize(content_file)
            # Round capacity to the next larger multiple of 8 MB
            # just to be safe...
            capacity = "{0}M".format(((capacity/1024/1024/8) + 1)*8)
            logger.verbose(
                "To contain files {0}, disk capacity of {1} will be {2}"
                .format(contents, file_path, capacity))
        logger.info("Calling fatdisk to create and format a raw disk image")
        self.call_helper([file_path, 'format', 'size', capacity, 'fat32'])
        for content_file in contents:
            logger.verbose("Calling fatdisk to add {0} to the image"
                           .format(content_file))
            self.call_helper([file_path, 'fileadd', content_file,
                              os.path.basename(content_file)])
        logger.info("All requested files successfully added to {0}"
                    .format(file_path))
