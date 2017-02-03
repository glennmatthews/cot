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

"""Wrapper classes to abstract away differences between file sources."""

import logging
import os
import shutil
import tarfile

from contextlib import closing

logger = logging.getLogger(__name__)


class FileOnDisk(object):
    """Wrapper for a 'real' file on disk."""

    def __init__(self, file_path, filename=None):
        """Create a reference to a file on disk.

        Args:
          file_path (str): File path or directory path
          filename (str): If specified, file_path is considered to be a
              directory containing this filename. If not specified, the
              final element in file_path is considered the filename.

        Raises:
          IOError: if no such file exists

        Examples:
          ::

            >>> a = FileOnDisk('/etc/resolv.conf')
            >>> b = FileOnDisk('/etc', 'resolv.conf')
            >>> a == b
            True

        """
        if filename is None:
            self.file_path = file_path
            self.filename = os.path.basename(file_path)
        else:
            self.file_path = os.path.join(file_path, filename)
            self.filename = filename
        if not self.exists:
            raise IOError("File {0} does not exist!".format(self.file_path))
        self.obj = None

    def __eq__(self, other):
        """FileOnDisk instances are equal if they point to the same path.

        No attempt is made to check file equivalence, symlinks, etc.

        Args:
          other (object): Other object to compare against
        Returns:
          bool: True if the paths are the same, else False
        """
        return type(other) is type(self) and self.file_path == other.file_path

    def __ne__(self, other):
        """FileOnDisk instances are not equal if they have different paths.

        Args:
          other (object): Other object to compare against
        Returns:
          bool: False if the paths are the same, else True
        """
        return not self.__eq__(other)

    @property
    def exists(self):
        """True if the file exists on disk, else False."""
        return os.path.exists(self.file_path)

    @property
    def size(self):
        """The size of this file, in bytes."""
        return os.path.getsize(self.file_path)

    def open(self, mode):
        """Open the file and return a reference to the file object.

        Args:
          mode (str): Mode such as 'r', 'w', 'a', 'w+', etc.
        Returns:
          file: File object
        """
        self.obj = open(self.file_path, mode)
        return self.obj

    def close(self):
        """Close the file previously opened."""
        self.obj.close()

    def copy_to(self, dest_dir):
        """Copy this file to the given destination directory.

        Args:
          dest_dir (str): Destination directory or filename.
        """
        if self.file_path == os.path.join(dest_dir, self.filename):
            return
        logger.info("Copying %s to %s", self.file_path, dest_dir)
        shutil.copy(self.file_path, dest_dir)

    def add_to_archive(self, tarf):
        """Copy this file into the given tarfile object.

        Args:
          tarf (tarfile.TarFile): Add this file to that archive.
        """
        logger.info("Adding %s to TAR file as %s",
                    self.file_path, self.filename)
        tarf.add(self.file_path, self.filename)


class FileInTAR(object):
    """Wrapper for a file inside a TAR archive or OVA."""

    def __init__(self, tarfile_path, filename):
        """Create a reference to a file contained in a TAR archive.

        Args:
          tarfile_path (str): Path to TAR archive to read
          filename (str): File name in the TAR archive.

        Raises:
          IOError: if ``tarfile_path`` doesn't reference a TAR file,
              or the TAR file does not contain ``filename``.
        """
        if not tarfile.is_tarfile(tarfile_path):
            raise IOError("{0} is not a valid TAR file.".format(tarfile_path))
        self.tarfile_path = tarfile_path
        self.filename = os.path.normpath(filename)
        if not self.exists:
            raise IOError("{0} does not exist in {1}"
                          .format(filename, tarfile_path))
        self.file_path = None
        self.tarf = None
        self.obj = None

    def __eq__(self, other):
        """FileInTAR are equal if they have the same filename and tarfile.

        No attempt is made to check file equivalence, symlinks, etc.

        Args:
          other (object): Other object to compare against
        Returns:
          bool: True if filename and tarfile_path are the same, else False
        """
        if type(other) is type(self):
            return (self.tarfile_path == other.tarfile_path and
                    self.filename == other.filename)
        return False

    def __ne__(self, other):
        """FileInTar are not equal if they have different paths or names.

        Args:
          other (object): Other object to compare against
        Returns:
          bool: False if filename and tarfile_path are the same, else True
        """
        return not self.__eq__(other)

    @property
    def exists(self):
        """True if the file exists in the TAR archive, else False."""
        with closing(tarfile.open(self.tarfile_path, 'r')) as tarf:
            try:
                tarf.getmember(self.filename)
                return True
            except KeyError:
                # Perhaps an issue with 'foo.txt' versus './foo.txt'?
                for mem in tarf.getmembers():
                    if os.path.normpath(mem.name) == self.filename:
                        logger.verbose("Found {0} at {1} in TAR file"
                                       .format(self.filename, mem.name))
                        self.filename = mem.name
                        return True
                return False

    @property
    def size(self):
        """The size of this file in bytes."""
        with closing(tarfile.open(self.tarfile_path, 'r')) as tarf:
            return tarf.getmember(self.filename).size

    def open(self, mode):
        """Open the TAR and return a reference to the relevant file object.

        Args:
          mode (str): Only 'r' and 'rb' modes are supported.
        Returns:
          file: File object
        Raises:
          ValueError: if ``mode`` is not valid.
        """
        # We can only extract a file object from a TAR file in read mode.
        if mode != 'r' and mode != 'rb':
            raise ValueError("FileInTar.open() only supports 'r'/'rb' mode")
        self.tarf = tarfile.open(self.tarfile_path, 'r')
        self.obj = self.tarf.extractfile(self.filename)
        return self.obj

    def close(self):
        """Close the file object previously opened."""
        if self.tarf is not None:
            self.tarf.close()
            self.tarf = None
        if self.obj is not None:
            self.obj.close()
            self.obj = None

    def copy_to(self, dest_dir):
        """Extract this file to the given destination directory.

        Args:
          dest_dir (str): Destination directory or filename.
        """
        with closing(tarfile.open(self.tarfile_path, 'r')) as tarf:
            logger.info("Extracting %s from %s to %s",
                        self.filename, self.tarfile_path, dest_dir)
            tarf.extract(self.filename, dest_dir)

    def add_to_archive(self, tarf):
        """Copy this file into the given tarfile object.

        Args:
          tarf (tarfile.TarFile): Add this file to that archive.
        """
        self.open('r')
        try:
            logger.info("Copying %s directly from %s to TAR file",
                        self.filename, self.tarfile_path)
            tarf.addfile(self.tarf.getmember(self.filename), self.obj)
        finally:
            self.close()


if __name__ == "__main__":
    import doctest
    doctest.testmod()
