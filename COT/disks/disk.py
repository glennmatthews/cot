# October 2016, Glenn F. Matthews
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
        """List of subclasses of DiskRepresentation.

        Wraps the :meth:`class.__subclasses__` builtin.
        """
        # pylint doesn't know about __subclasses__
        # https://github.com/PyCQA/pylint/issues/555
        # TODO: this should be fixed when pylint 2.0 is released
        # pylint:disable=no-member
        return DiskRepresentation.__subclasses__()

    @staticmethod
    def class_for_format(disk_format):
        """Get the DiskRepresentation subclass associated with the given format.

        Args:
          disk_format (str): Disk format string such as 'iso' or 'vmdk'

        Returns:
          DiskRepresentation: appropriate subclass object.
        """
        return next((subclass for subclass in DiskRepresentation.subclasses()
                     if subclass.disk_format == disk_format),
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
        for subclass in DiskRepresentation.subclasses():
            confidence = subclass.file_is_this_type(path)
            if confidence > best_confidence:
                logger.debug("File %s may be a %s, with confidence %d%%",
                             path, subclass.disk_format, confidence)
                best_guess = subclass
                best_confidence = confidence
            elif confidence > 0 and confidence == best_confidence:
                logger.warning("For file %s, same confidence level (%d%%) for "
                               "classes %s and %s. Using %s",
                               path, confidence, best_guess,
                               subclass, best_guess)
        if best_guess is not None:
            logger.verbose("File %s appears to be a %s, with confidence %s%%",
                           path, best_guess.disk_format, best_confidence)
            if best_confidence < 50:
                logger.warning("File %s has been guessed to be a %s disk "
                               "image, but COT has low confidence (%s%%) "
                               "in this guess.",
                               path, best_guess.disk_format, best_confidence)
            return best_guess(path)
        else:
            raise NotImplementedError("No support for files of this type")

    @classmethod
    def for_new_file(cls, path, disk_format, **kwargs):
        """Create a new disk file and return a DiskRepresentation.

        Args:
          path (str): Path to create file at.
          disk_format (str): Disk format to create, such as 'iso' or 'vmdk'.
          **kwargs: Arguments to pass through to appropriate DiskRepresentation
            subclass for this format.

        Returns:
          DiskRepresentation: representation of the created file.

        Raises:
          NotImplementedError: if ``disk_format`` is not supported.
        """
        if cls.disk_format != disk_format:
            cls = cls.class_for_format(disk_format)
            if cls is None:
                raise NotImplementedError("No support for files of type '{0}'"
                                          .format(disk_format))
        cls.create_file(path, **kwargs)
        return cls(path)

    def __init__(self, path):
        """Create a representation of an existing disk.

        Args:
          path (str): Path to existing file.
        """
        if not path:
            raise ValueError("Path must be set to a valid value, but got {0}"
                             .format(path))
        if not os.path.exists(path):
            raise HelperError(2, "No such file or directory: '{0}'"
                              .format(path))
        self._path = path
        self._disk_subformat = None
        self._capacity = None
        self._files = None

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
            logger.debug("Disk %s capacity is %s bytes", self.path,
                         self._capacity)
        return self._capacity

    @property
    def files(self):
        """List of files embedded in this disk image."""
        if self._files is not None:
            return self._files
        raise NotImplementedError("Unable to determine file contents")

    @property
    def predicted_drive_type(self):
        """Disk drive type typically used for a Disk of this type.

        Returns:
          str: 'cdrom' or 'harddisk'
        """
        # Default for most Disk types
        return 'harddisk'

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
        assert os.path.isdir(new_directory)
        subclass = self.class_for_format(new_format)
        if subclass is None:
            raise NotImplementedError("No support for converting to type '{0}'"
                                      .format(new_format))
        return subclass.from_other_image(self, new_directory, new_subformat)

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
        logger.debug("Using 'qemu-img' to check whether %s is a %s",
                     path, cls.disk_format)
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

    @classmethod
    def create_file(cls, path, files=None, capacity=None, **kwargs):
        """Create a new disk image file of this type.

        Args:
          path (str): Location to create disk file.
          files (list): List of files to include in the disk's filesystem.
          capacity (str): Disk capacity.
          **kwargs: Subclasses and :meth:`_create_file` may accept additional
            parameters.

        Raises:
          ValueError: if path is not a valid string
          RuntimeError: if a file already exists at path.
          RuntimeError: if neither files nor capacity is specified
        """
        if not path:
            raise ValueError("Path must be set to a valid value, but got {0}"
                             .format(path))
        if os.path.exists(path):
            raise RuntimeError("File already exists at {0}".format(path))
        if capacity is None and files is None:
            raise RuntimeError("Capacity and/or files must be specified!")
        cls._create_file(path, files=files, capacity=capacity, **kwargs)

    @classmethod
    def _create_file(cls, path, files=None, capacity=None, disk_subformat=None,
                     **kwargs):
        """Default worker function for create_file().

        Creates a blank disk using ``qemu-img``.
        Subclasses can override this method if needed.

        Args:
          path (str): Location to create disk file.
          files (list): List of files to include in the disk's filesystem.
          capacity (str): Disk capacity.
          disk_subformat (str): Disk subformat such as 'streamOptimized'.
          **kwargs: Subclasses may accept additional parameters.

        Raises:
          NotImplementedError: this generic implementation doesn't know how to
            handle any non-empty value for ``files``.
        """
        # pylint: disable=unused-argument

        # Default implementation - create a blank disk using qemu-img
        if files:
            raise NotImplementedError("Don't know how to create a disk of "
                                      "this format containing a filesystem")
        args = ['create', '-f', cls.disk_format]
        if disk_subformat is not None:
            args += ['-o', 'subformat=' + disk_subformat]
        args += [path, capacity]
        helpers['qemu-img'].call(args)
