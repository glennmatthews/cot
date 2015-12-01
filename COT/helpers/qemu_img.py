#!/usr/bin/env python
#
# qemu_img.py - Helper for 'qemu-img'
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

"""Give COT access to ``qemu-img`` for manipulating disk image formats.

http://www.qemu.org
"""

import logging
import os.path
import re
from distutils.version import StrictVersion

from .helper import Helper

logger = logging.getLogger(__name__)


class QEMUImg(Helper):
    """Helper provider for ``qemu-img`` (http://www.qemu.org).

    **Methods**

    .. autosummary::
      :nosignatures:

      install_helper
      get_disk_format
      get_disk_capacity
      convert_disk_image
      create_blank_disk
    """

    def __init__(self):
        """Initializer."""
        super(QEMUImg, self).__init__(
            "qemu-img",
            version_regexp="qemu-img version ([0-9.]+)")
        self.vmdktool = None

    def install_helper(self):
        """Install ``qemu-img``."""
        if self.path:
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.name, self.path))
            return
        logger.info("Installing 'qemu-img'...")
        if not (Helper.apt_install('qemu-utils') or
                Helper.port_install('qemu') or
                Helper.yum_install('qemu-img')):
            raise NotImplementedError(
                "Unsure how to install qemu-img.\n"
                "See http://en.wikibooks.org/wiki/QEMU/Installing_QEMU")
        logger.info("Successfully installed 'qemu-img'.")

    def get_disk_format(self, file_path):
        """Get the major disk image format of the given file.

        .. warning::
          If :attr:`file_path` refers to a file which is not a disk image at
          all, this function will return ``'raw'``.

        :param str file_path: Path to disk image file to inspect.
        :return: Disk image format (``'vmdk'``, ``'raw'``, ``'qcow2'``, etc.)
        """
        output = self.call_helper(['info', file_path])
        # Read the format from the output
        match = re.search("file format: (\S*)", output)
        if not match:
            raise RuntimeError("Did not find file format string in "
                               "the output from qemu-img:\n{0}"
                               .format(output))
        file_format = match.group(1)
        logger.info("File format of '{0}' is '{1}'"
                    .format(os.path.basename(file_path), file_format))
        return file_format

    def get_disk_capacity(self, file_path):
        """Get the storage capacity of the given disk image.

        :param str file_path: Path to disk image file to inspect
        :return: Disk capacity, in bytes
        """
        output = self.call_helper(['info', file_path])
        match = re.search(r"(\d+) bytes", output)
        if not match:
            raise RuntimeError("Did not find byte count in the output from "
                               "qemu-img:\n{0}"
                               .format(output))
        capacity = match.group(1)
        logger.verbose("Disk {0} capacity is {1} bytes".format(file_path,
                                                               capacity))
        return capacity

    def convert_disk_image(self, file_path, output_dir,
                           new_format, new_subformat=None):
        """Convert the given disk image to the requested format/subformat.

        If the disk is already in this format then it is unchanged;
        otherwise, will convert to a new disk in the specified output_dir
        and return its path.

        Current supported conversions:

        * .vmdk (any format) to .vmdk (streamOptimized)
        * .img to .vmdk (streamOptimized)

        :param str file_path: Disk image file to inspect/convert
        :param str output_dir: Directory to place converted image into, if
          needed
        :param str new_format: Desired final format
        :param str new_subformat: Desired final subformat
        :return:
          * :attr:`file_path`, if no conversion was required
          * or a file path in :attr:`output_dir` containing the converted image

        :raise NotImplementedError: if the :attr:`new_format` and/or
          :attr:`new_subformat` are not supported conversion targets.
        """
        file_name = os.path.basename(file_path)
        (file_string, file_extension) = os.path.splitext(file_name)

        new_file_path = None
        if new_format == 'raw':
            new_file_path = os.path.join(output_dir, file_string + '.img')
            logger.info("Invoking qemu-img to convert {0} into raw image {1}"
                        .format(file_path, new_file_path))
            self.call_helper(['convert', '-O', 'raw',
                              file_path, new_file_path])
        elif new_format == 'vmdk' and new_subformat == 'streamOptimized':
            if self.version >= StrictVersion("2.1.0"):
                new_file_path = os.path.join(output_dir, file_string + '.vmdk')
                # qemu-img finally supports streamOptimized - yay!
                logger.info("Invoking qemu-img to convert {0} to "
                            "streamOptimized VMDK {1}"
                            .format(file_path, new_file_path))
                self.call_helper(['convert', '-O', 'vmdk',
                                  '-o', 'subformat=streamOptimized',
                                  file_path, new_file_path])
            else:
                raise NotImplementedError("qemu-img is unable to convert to "
                                          "stream-optimized VMDK format prior "
                                          "to version 2.1.0 - you have {0}"
                                          .format(self.version))
        else:
            raise NotImplementedError("No support for converting disk image "
                                      "to format {0} / subformat {1}"
                                      .format(new_format, new_subformat))

        return new_file_path

    def create_blank_disk(self, file_path, capacity, file_format=None):
        """Create an unformatted disk image at the requested location.

        :param str file_path: Desired location of new disk image
        :param capacity: Disk capacity. A string like '16M' or '1G'.
        :param str file_format: Desired image format (if not specified, this
          will be derived from the file extension of :attr:`file_path`)
        """
        if not file_format:
            # Guess format from file extension
            file_format = os.path.splitext(file_path)[1][1:]
            if not file_format:
                raise RuntimeError(
                    "Unable to guess file format from desired filename {0}"
                    .format(file_path))
            if file_format == 'img':
                file_format = 'raw'
            logger.debug("Guessed file format is {0}".format(file_format))

        logger.info("Calling qemu-img to create {0} {1} image"
                    .format(capacity, file_format))
        self.call_helper(['create', '-f', file_format,
                          file_path, capacity])
