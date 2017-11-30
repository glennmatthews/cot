#!/usr/bin/env python
#
# file_reference.py - APIs abstracting away various ways to refer to a file.
#
# August 2015, Glenn F. Matthews
# Copyright (c) 2015-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Wrapper classes to abstract away differences between file sources.

**Classes**

.. autosummary::
  :nosignatures:

  FileReference
  FileOnDisk
  FileInTAR
"""

import logging
import os
import shutil
import tarfile

from contextlib import contextmanager, closing

from COT.data_validation import file_checksum

logger = logging.getLogger(__name__)


class FileReference(object):
    """Semi-abstract base class for file references."""

    @classmethod
    def create(cls, container_path, filename, **kwargs):
        """Create a reference to a file in a container of some sort.

        Args:
          container_path (str): Absolute path to a container such as a
            directory or a TAR file.
          filename (str): Name of file within the container in question.
          **kwargs: See :meth:__init__()

        Returns:
          FileReference: instance of appropriate subclass
        """
        if not os.path.isabs(container_path):
            logger.warning("Only absolute paths are accepted, but "
                           'got apparent relative path "%s".'
                           "\nAttempting to convert it to an absolute path.",
                           container_path)
            container_path = os.path.abspath(container_path)
        if not os.path.exists(container_path):
            raise IOError("Container path '{0}' does not exist"
                          .format(container_path))
        if os.path.isdir(container_path):
            return FileOnDisk(container_path, filename, **kwargs)
        elif tarfile.is_tarfile(container_path):
            return FileInTAR(container_path, filename, **kwargs)
        else:
            raise NotImplementedError("Don't know how to open container {0}!"
                                      .format(container_path))

    def __init__(self,
                 container_path,
                 filename,
                 checksum_algorithm=None,
                 expected_checksum=None,
                 expected_size=None):
        """Common initialization and validation logic.

        Args:
          container_path (str): Path to container (directory, TAR file, etc.)
          filename (str): Relative path within the container to the file itself
          checksum_algorithm (str): 'sha1', 'sha256', etc.
          expected_checksum (str): Expected checksum of the file, if any.
          expected_size (int): Expected size of the file, in bytes, if any.

        Raises:
          IOError: if the file does not actually exist or is not readable.
        """
        if not os.path.isabs(container_path):
            logger.warning("Only absolute paths are accepted, but "
                           'got apparent relative path "%s".'
                           "\nAttempting to convert it to an absolute path.",
                           container_path)
            container_path = os.path.abspath(container_path)
        self.container_path = container_path
        self.filename = os.path.normpath(filename)
        self.checksum_algorithm = checksum_algorithm
        self._checksum = None
        self._size = None
        self.force_refresh = False

        logger.spam("Initing for file %s, expected_size %s,"
                    " expected_checksum %s",
                    self.filename, expected_size, expected_checksum)

        if not self.exists:
            raise IOError("File '{0}' does not exist in {1}"
                          .format(self.filename, self.container_path))

        if expected_checksum is not None and (self.checksum !=
                                              expected_checksum):
            logger.error("The %s checksum for file '%s' is expected to be:"
                         "\n%s\nbut is actually:\n%s\n"
                         "This file may have been tampered with!",
                         self.checksum_algorithm,
                         self.filename,
                         expected_checksum,
                         self.checksum)

        if expected_size is not None and self.size != int(expected_size):
            logger.warning("The size of file '%s' is expected to be %s bytes,"
                           " but is actually %s bytes.",
                           self.filename, expected_size, self.size)

        # Should never fail this:
        assert self.exists

    @property
    def checksum(self):
        """Checksum of the referenced file."""
        if self.checksum_algorithm is None:
            return None
        if self._checksum is None or self.force_refresh:
            with self.open('rb') as file_obj:
                self._checksum = file_checksum(file_obj,
                                               self.checksum_algorithm)
        return self._checksum

    @property
    def exists(self):
        """Report whether this file actually exists."""
        raise NotImplementedError

    @property
    def file_path(self):
        """Actual path to a real file, if any."""
        return None

    @property
    def size(self):
        """Size of the referenced file, in bytes."""
        raise NotImplementedError

    @contextmanager
    def open(self, mode):
        """Open the file and yield a reference to the file object.

        Automatically closes the file when done.
        Some subclasses may not support all modes.

        Args:
          mode (str): Mode such as 'r', 'w', 'a', 'w+', etc.
        Yields:
          file: File object
        """
        raise NotImplementedError

    def refresh(self):
        """Make sure all information in this reference is still valid."""
        # Cache the previously known values
        exp_size = self.size
        exp_checksum = self.checksum
        logger.spam("Refreshing FileReference for '%s', "
                    "expected size %s, cksum %s",
                    self.filename, exp_size, exp_checksum)
        result = True

        self.force_refresh = True

        if not self.exists:
            logger.error("File '%s' no longer exists!", self.filename)
            # keep force_refresh as True since we're in a bad state
            return False

        # Refresh the attributes and see if they've changed
        if self.size != exp_size and exp_size is not None:
            logger.warning("Size of file '%s' has changed"
                           " from %s bytes to %s bytes.",
                           self.filename, exp_size, self.size)
            result = False

        if self.checksum != exp_checksum and exp_checksum is not None:
            logger.error("The %s checksum of file '%s' has changed"
                         " from\n%s\nto\n%s\n"
                         "This file may have been tampered with!",
                         self.checksum_algorithm, self.filename,
                         exp_checksum, self.checksum)
            result = False

        return result


class FileOnDisk(FileReference):
    """Wrapper for a 'real' file on disk."""

    @property
    def file_path(self):
        """Directory + filename."""
        return os.path.join(self.container_path, self.filename)

    @property
    def exists(self):
        """True if the file exists on disk, else False."""
        return os.path.exists(self.file_path)

    @property
    def size(self):
        """The size of this file, in bytes."""
        if self._size is None or self.force_refresh:
            self._size = os.path.getsize(self.file_path)
        return self._size

    @contextmanager
    def open(self, mode):
        """Open the file and return a reference to the file object.

        Args:
          mode (str): Mode such as 'r', 'w', 'a', 'w+', etc.
        Yields:
          file: File object
        """
        with open(self.file_path, mode) as obj:
            yield obj

    def copy_to(self, dest_dir):
        """Copy this file to the given destination directory.

        Args:
          dest_dir (str): Destination directory or filename.
        """
        if self.file_path == os.path.join(dest_dir, self.filename):
            return
        logger.debug("Copying %s to %s", self.file_path, dest_dir)
        shutil.copy(self.file_path, dest_dir)

    def add_to_archive(self, tarf):
        """Copy this file into the given tarfile object.

        Args:
          tarf (tarfile.TarFile): Add this file to that archive.
        """
        logger.debug("Adding %s to TAR file as %s",
                     self.file_path, self.filename)
        tarf.add(self.file_path, self.filename)


class FileInTAR(FileReference):
    """Wrapper for a file inside a TAR archive or OVA."""

    def __init__(self, tarfile_path, filename, **kwargs):
        """Create a reference to a file contained in a TAR archive.

        Args:
          tarfile_path (str): Path to TAR archive to read
          filename (str): File name in the TAR archive.
          **kwargs: Passed through to :meth:`FileReference.__init__`.

        Raises:
          IOError: if ``tarfile_path`` doesn't reference a TAR file,
              or the TAR file does not contain ``filename``.
        """
        if not os.path.isabs(tarfile_path):
            logger.warning("Only absolute paths are accepted, but "
                           'got apparent relative path "%s".'
                           "\nAttempting to convert it to an absolute path.",
                           tarfile_path)
            tarfile_path = os.path.abspath(tarfile_path)
        if not tarfile.is_tarfile(tarfile_path):
            raise IOError("{0} is not a valid TAR file.".format(tarfile_path))
        self.tarf = None
        super(FileInTAR, self).__init__(tarfile_path, filename, **kwargs)

    @property
    def exists(self):
        """True if the file exists in the TAR archive, else False."""
        with tarfile.open(self.container_path, 'r') as tarf:
            try:
                tarf.getmember(self.filename)
                return True
            except KeyError:
                # Perhaps an issue with 'foo.txt' versus './foo.txt'?
                for mem in tarf.getmembers():
                    if os.path.normpath(mem.name) == self.filename:
                        logger.debug("Found %s at %s in TAR file",
                                     self.filename, mem.name)
                        self.filename = mem.name
                        return True
                return False

    @property
    def size(self):
        """The size of this file in bytes."""
        if self._size is None or self.force_refresh:
            with tarfile.open(self.container_path, 'r') as tarf:
                self._size = tarf.getmember(self.filename).size
        return self._size

    @contextmanager
    def open(self, mode):
        """Open the TAR and return a reference to the relevant file object.

        Args:
          mode (str): Only 'r' and 'rb' modes are supported.
        Yields:
          file: File object
        Raises:
          ValueError: if ``mode`` is not valid.
        """
        # We can only extract a file object from a TAR file in read mode.
        if mode != 'r' and mode != 'rb':
            raise ValueError("FileInTar.open() only supports 'r'/'rb' mode")
        # actually tarf.extractfile is always a binary object...
        with tarfile.open(self.container_path, 'r') as tarf:
            self.tarf = tarf
            with closing(tarf.extractfile(self.filename)) as obj:
                yield obj
        self.tarf = None

    def copy_to(self, dest_dir):
        """Extract this file to the given destination directory.

        Args:
          dest_dir (str): Destination directory or filename.
        """
        with tarfile.open(self.container_path, 'r') as tarf:
            logger.debug("Extracting %s from %s to %s",
                         self.filename, self.container_path, dest_dir)
            tarf.extract(self.filename, dest_dir)

    def add_to_archive(self, tarf):
        """Copy this file into the given tarfile object.

        Args:
          tarf (tarfile.TarFile): Add this file to that archive.
        """
        with self.open('r') as obj:
            logger.debug("Copying %s directly from %s to TAR file",
                         self.filename, self.container_path)
            tarf.addfile(self.tarf.getmember(self.filename), obj)
