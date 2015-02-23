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

import logging
import os.path
import re
import shutil
import sys
from distutils.spawn import find_executable
from distutils.version import StrictVersion

from .helper import Helper

logger = logging.getLogger(__name__)


class FatDisk(Helper):

    def __init__(self):
        super(FatDisk, self).__init__("fatdisk")

    def _get_version(self):
        output = self.call_helper(['--version'])
        match = re.search("version ([0-9.]+)", output)
        return StrictVersion(match.group(1))

    def install_helper(self):
        if self.find_helper():
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.helper, self.helper_path))
            return
        if self.PACKAGE_MANAGERS['port']:
            self._check_call(['sudo', 'port', 'install', 'fatdisk'])
        elif sys.platform == 'linux2':
            # Fatdisk installation requires make
            if not find_executable('make'):
                if self.PACKAGE_MANAGERS['apt-get']:
                    self._check_call(['sudo', 'apt-get', 'install', 'make'])
                else:
                    raise NotImplementedError("Not sure how to install 'make'")
            self._check_call(
                ['wget', '-O', 'fatdisk.tgz', 'https://github.com/goblinhack/'
                 'fatdisk/archive/master.tar.gz'])
            self._check_call(['tar', 'zxf', 'fatdisk.tgz'])
            self._check_call(['./RUNME'], cwd='fatdisk-master')
            shutil.copy2('fatdisk-master/fatdisk', '/usr/local/bin/fatdisk')
        else:
            raise NotImplementedError(
                "Not sure how to install 'fatdisk'.\n"
                "See https://github.com/goblinhack/fatdisk")

    def create_raw_image(self, file_path, contents, capacity=None):
        """Create a new FAT32-formatted raw image at the requested location.

        :param str file_path: Desired location of new disk image
        :param list contents: List of file paths to package into the created
          image.
        :param capacity: TODO what's the expected format?
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
