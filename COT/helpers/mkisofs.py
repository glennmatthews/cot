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

"""Give COT access to ``mkisofs`` or ``genisoimage`` for creating ISO images.

http://cdrecord.org/
"""

import logging

from .helper import Helper

logger = logging.getLogger(__name__)


class MkIsoFS(Helper):

    """Helper provider for ``mkisofs`` and/or ``genisoimage``.

    http://cdrecord.org/

    **Methods**

    .. autosummary::
      :nosignatures:

      find_helper
      install_helper
      create_iso
    """

    def __init__(self):
        """Initializer."""
        super(MkIsoFS, self).__init__("mkisofs",
                                      version_regexp="mkisofs ([0-9.]+)")

    def find_helper(self):
        """Find either ``mkisofs`` or ``genisoimage`` if available."""
        if super(MkIsoFS, self).find_helper():
            return True
        elif self.helper == "mkisofs":
            # Try 'genisoimage' as an alternative
            self.helper = "genisoimage"
            return super(MkIsoFS, self).find_helper()
        elif self.helper == "genisoimage":
            # Try 'mkisofs' as an alternative
            self.helper = "mkisofs"
            return super(MkIsoFS, self).find_helper()
        return False

    def install_helper(self):
        """Install ``mkisofs`` and/or ``genisoimage``."""
        if self.find_helper():
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.helper, self.helper_path))
            return
        logger.info("Installing 'mkisofs' and/or 'genisoimage'...")
        if self.port_install('cdrtools'):
            self.helper = 'mkisofs'
        elif (self.apt_install('genisoimage') or
              self.yum_install('genisoimage')):
            self.helper = "genisoimage"
        else:
            raise NotImplementedError(
                "Unsure how to install mkisofs.\n"
                "See http://cdrecord.org/")
        logger.info("Successfully installed '{0}'".format(self.helper))

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
