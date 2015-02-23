#!/usr/bin/env python
#
# mkisofs.py - Helper for 'mkisofs' and 'genisoimage'
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
import re
from distutils.version import StrictVersion

from .helper import Helper

logger = logging.getLogger(__name__)


class MkIsoFS(Helper):

    def __init__(self):
        super(MkIsoFS, self).__init__("mkisofs")

    def _get_version(self):
        output = self.call_helper(['--version'])
        match = re.search("mkisofs ([0-9.]+)", output)
        return StrictVersion(match.group(1))

    def find_helper(self):
        if super(MkIsoFS, self).find_helper():
            return True
        elif self.helper == "mkisofs":
            # Try 'genisoimage' as an alternative
            self.helper = "genisoimage"
            return super(MkIsoFS, self).find_helper()
        return False

    def install_helper(self):
        if self.find_helper():
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.helper, self.helper_path))
            return
        if self.PACKAGE_MANAGERS['apt-get']:
            self._check_call(['sudo', 'apt-get', 'install', 'genisoimage'])
            self.helper = "genisoimage"
        elif self.PACKAGE_MANAGERS['port']:
            self._check_call(['sudo', 'port', 'install', 'cdrtools'])
        else:
            raise NotImplementedError(
                "Unsure how to install mkisofs.\n"
                "See http://cdrecord.org/")

    def create_iso(self, file_path, contents):
        """Create a new ISO image at the requested location.

        :param str file_path: Desired location of new disk image
        :param list contents: List of file paths to package into the created
          image.
        """
        logger.info("Calling {0} to create an ISO image"
                    .format(self.helper))
        # mkisofs and genisoimage take the same parameters, conveniently
        self.call_helper(['-output', file_path,
                          '-full-iso9660-filenames',
                          '-iso-level', '2'] + contents)
