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

"""Give COT access to mkisofs, genisoimage, or xorriso for creating ISO images.

http://cdrecord.org/
https://www.gnu.org/software/xorriso/
"""

import logging

from .helper import Helper

logger = logging.getLogger(__name__)


class MkIsoFS(Helper):
    """Helper provider for ``mkisofs``, ``genisoimage``, or ``xorriso``.

    http://cdrecord.org/
    https://www.gnu.org/software/xorriso/

    **Methods**

    .. autosummary::
      :nosignatures:

      install_helper
      create_iso
    """

    def __init__(self):
        """Initializer."""
        super(MkIsoFS, self).__init__(
            "mkisofs",
            version_regexp="(?:mkisofs|genisoimage|xorriso) ([0-9.]+)")

    @property
    def name(self):
        """Either mkisofs, genisoimage, or xorriso depending on environment."""
        if not self._path:
            self._path = self.find_executable("mkisofs")
            if self._path:
                self._name = "mkisofs"
        if not self._path:
            self._path = self.find_executable("genisoimage")
            if self._path:
                self._name = "genisoimage"
        if not self._path:
            self._path = self.find_executable("xorriso")
            if self._path:
                self._name = "xorriso"
        return self._name

    @property
    def path(self):
        """Find ``mkisofs``, ``genisoimage``, or ``xorriso`` if available."""
        self.name
        return self._path

    def install_helper(self):
        """Install ``mkisofs``, ``genisoimage``, or ``xorriso``."""
        if self.path:
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.name, self.path))
            return
        logger.info("Installing 'mkisofs' and/or 'genisoimage'...")
        if Helper.port_install('cdrtools'):
            self._name = 'mkisofs'
        elif (Helper.apt_install('genisoimage') or
              Helper.yum_install('genisoimage')):
            self._name = "genisoimage"
        elif Helper.apt_install('xorriso'):
            self._name = "xorriso"
        else:
            raise NotImplementedError(
                "Unsure how to install mkisofs.\n"
                "See http://cdrecord.org/")
        logger.info("Successfully installed '{0}'".format(self.name))

    def create_iso(self, file_path, contents):
        """Create a new ISO image at the requested location.

        :param str file_path: Desired location of new disk image
        :param list contents: List of file paths to package into the created
          image.
        """
        logger.info("Calling {0} to create an ISO image"
                    .format(self.name))
        # mkisofs and genisoimage take the same parameters, conveniently,
        # while xorriso needs to be asked to pretend to be mkisofs
        args = ['-output', file_path, '-full-iso9660-filenames',
                '-iso-level', '2'] + contents
        if self.name == 'xorriso':
            args = ['-as', 'mkisofs'] + args
        self.call_helper(args)
