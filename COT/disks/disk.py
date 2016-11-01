# October 2016, Glenn F. Matthews
# Copyright (c) 2013-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Abstract base class for representations of disk image files."""

import logging
import os
import re

from COT.helpers import helpers, HelperError

logger = logging.getLogger(__name__)


class DiskRepresentation(object):
    """Abstract disk image file representation."""

    disk_format = None
    """Disk format represented by this class."""

    def __init__(self, path,
                 disk_subformat=None,
                 capacity=None,
                 files=None):
        """Create a representation of an existing disk or create a new disk.

        Args:
          path (str): Path to existing file or path to create new file at.
          disk_subformat (str): Subformat option(s) of the disk to create
              (e.g., 'rockridge' for ISO, 'streamOptimized' for VMDK), if any.
          capacity (int): Capacity of disk to create
          files (int): Files to place in the filesystem of this disk.
        """
        if not path:
            raise ValueError("Path must be set to a valid value, but got {0}"
                             .format(path))
        self._path = path
        self._disk_subformat = disk_subformat
        self._capacity = capacity
        self._files = files
        if not os.path.exists(path):
            self.create_file()

    @property
    def path(self):
        """System path to this disk file."""
        return self._path

    @property
    def disk_subformat(self):
        """Sub-format of the disk, such as 'rockridge' or 'streamOptimized'."""
        return self._disk_subformat

    @property
    def capacity(self):
        """Capacity of this disk image, in bytes."""
        # default implementation - qemu-img handles most types we need
        if self._capacity is None:
            output = helpers['qemu-img'].call(['info', self.path])
            match = re.search(r"(\d+) bytes", output)
            if not match:
                raise RuntimeError("Did not find byte count in the output "
                                   "from qemu-img:\n{0}"
                                   .format(output))
            self._capacity = match.group(1)
            logger.verbose("Disk %s capacity is %s bytes", self.path,
                           self._capacity)
        return self._capacity

    @property
    def files(self):
        """List of files embedded in this disk image."""
        if self._files is not None:
            return self._files
        raise NotImplementedError("Unable to determine file contents")

    @classmethod
    def from_other_image(cls, input_image, output_dir, output_subformat=None):
        """Convert the other disk image into an image of this type.

        Args:
          input_image (DiskRepresentation): Existing image representation.
          output_dir (str): Output directory to store the new image in.
          output_subformat (str): Any relevant subformat information.

        Raises:
          NotImplementedError: Subclasses may implement this.
        """
        raise NotImplementedError("Not a valid target for conversion")

    @classmethod
    def file_is_this_type(cls, path):
        """Check if the given file is image type represented by this class.

        Args:
          path (str): Path to file to check.

        Returns:
          bool: True (file matches this type) or False (file does not match)

        Raises:
          HelperError: if no file exists at ``path``.
        """
        if not os.path.exists(path):
            raise HelperError(2, "No such file or directory: '{0}'"
                              .format(path))

        # Default implementation using qemu-img
        output = helpers['qemu-img'].call(['info', path])
        # Read the format from the output
        match = re.search(r"file format: (\S*)", output)
        if not match:
            raise RuntimeError("Did not find file format string in "
                               "the output from qemu-img:\n{0}"
                               .format(output))
        file_format = match.group(1)
        return file_format == cls.disk_format

    def create_file(self):
        """Given parameters but not an existing file, create that file."""
        if os.path.exists(self.path):
            raise RuntimeError("File already exists at {0}".format(self.path))
        if self._capacity is None and self._files is None:
            raise RuntimeError("Capacity and/or files must be specified!")
        self._create_file()

    def _create_file(self):
        """Worker function for create_file()."""
        # Default implementation - create a blank disk using qemu-img
        if self._files:
            raise NotImplementedError("Don't know how to create a disk of "
                                      "this format containing a filesystem")
        helpers['qemu-img'].call(['create', '-f', self.disk_format,
                                  self.path, self.capacity])
