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

    @staticmethod
    def subclasses():
        """Subclasses of DiskRepresentation. Wraps __subclasses__ builtin."""
        # pylint doesn't know about __subclasses__
        # https://github.com/PyCQA/pylint/issues/555
        # TODO: this should be fixed when pylint 2.0 is released
        # pylint:disable=no-member
        return DiskRepresentation.__subclasses__()

    @staticmethod
    def supported_disk_formats():
        """List of disk format strings with support."""
        return [sc.disk_format for sc in DiskRepresentation.subclasses()]

    @staticmethod
    def class_for_format(disk_format):
        """Get the DiskRepresentation subclass associated with the given format.

        Args:
          disk_format (str): Disk format string such as 'iso' or 'vmdk'

        Returns:
          DiskRepresentation: appropriate subclass object.
        """
        return next((sc for sc in DiskRepresentation.subclasses() if
                     sc.disk_format == disk_format),
                    None)

    @staticmethod
    def from_file(path):
        """Get a DiskRepresentation instance appropriate to the given file.

        Args:
          path (str): Path of existing file to represent.

        Returns:
          DiskRepresentation: Representation of this file.

        Raises:
          IOError: if no file exists at the given path
          NotImplementedError: if the file is not a supported type.
        """
        if not os.path.exists(path):
            raise IOError(2, "No such file or directory: {0}".format(path))
        best_guess = None
        best_confidence = 0
        for sc in DiskRepresentation.subclasses():
            confidence = sc.file_is_this_type(path)
            if confidence > best_confidence:
                logger.verbose("File %s may be a %s, with confidence %d",
                               path, sc.disk_format, confidence)
                best_guess = sc
                best_confidence = confidence
            elif confidence > 0 and confidence == best_confidence:
                logger.warning("For file %s, same confidence level (%d) for "
                               "classes %s and %s. Using %s",
                               path, confidence, best_guess,
                               sc, best_guess)
        if best_guess is not None:
            return best_guess(path)
        else:
            raise NotImplementedError("No support for files of this type")

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

    def convert_to(self, new_format, new_directory, new_subformat=None):
        """Convert the disk file to a new format and return the new instance.

        Args:
          new_format (str): Format to convert to.
          new_subformat (str): (optional) Sub-format to convert to.
          new_directory (str): Directory path to store new image into.

        Returns:
          DiskRepresentation: Converted disk

        Raises:
          NotImplementedError: if new_format is not a supported type

        .. seealso:: :meth:`from_other_image`
        """
        sc = self.class_for_format(new_format)
        if sc is None:
            raise NotImplementedError("No support for converting to type '{0}'"
                                      .format(new_format))
        return sc.from_other_image(self, new_directory, new_subformat)

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
          int: Confidence that this file matches. 0 is definitely not a match,
          100 is definitely a match.

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
        if file_format == cls.disk_format:
            return 100
        else:
            return 0

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
