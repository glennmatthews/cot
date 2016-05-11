#!/usr/bin/env python
#
# file_reference.py - APIs abstracting away various ways to refer to a file.
#
# August 2015, Glenn F. Matthews
# Copyright (c) 2015 the COT project developers.
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
        """Create a reference to a file on disk."""
        if filename is None:
            self.file_path = file_path
            self.filename = os.path.basename(file_path)
        else:
            self.file_path = os.path.join(file_path, filename)
            self.filename = filename
        if not self.exists():
            raise IOError("File {0} does not exist!".format(self.file_path))
        self.obj = None

    def exists(self):
        """Check whether the file exists on disk."""
        return os.path.exists(self.file_path)

    def size(self):
        """Get the size of this file, in bytes."""
        return os.path.getsize(self.file_path)

    def open(self, mode):
        """Open the file and return a reference to the file object."""
        self.obj = open(self.file_path, mode)
        return self.obj

    def close(self):
        """Close the file previously opened."""
        self.obj.close()

    def copy_to(self, dest_dir):
        """Copy this file to the given destination directory."""
        if self.file_path == os.path.join(dest_dir, self.filename):
            return
        logger.info("Copying {0} to {1}".format(self.file_path, dest_dir))
        shutil.copy(self.file_path, dest_dir)

    def add_to_archive(self, tarf):
        """Copy this file into the given tarfile object."""
        logger.info("Adding {0} to TAR file as {1}"
                    .format(self.file_path, self.filename))
        tarf.add(self.file_path, self.filename)


class FileInTAR(object):
    """Wrapper for a file inside a TAR archive or OVA."""

    def __init__(self, tarfile_path, filename):
        """Create a reference to a file contained in a TAR archive."""
        if not tarfile.is_tarfile(tarfile_path):
            raise IOError("{0} is not a valid TAR file.".format(tarfile_path))
        self.tarfile_path = tarfile_path
        self.filename = filename
        if not self.exists():
            raise IOError("{0} does not exist in {1}"
                          .format(filename, tarfile_path))
        self.file_path = None
        self.tarf = None
        self.obj = None

    def exists(self):
        """Check whether the file exists in the TAR archive."""
        with closing(tarfile.open(self.tarfile_path, 'r')) as tarf:
            try:
                tarf.getmember(self.filename)
                return True
            except KeyError:
                return False

    def size(self):
        """Get the size of this file in bytes."""
        with closing(tarfile.open(self.tarfile_path, 'r')) as tarf:
            return tarf.getmember(self.filename).size

    def open(self, mode):
        """Open the TAR and return a reference to the relevant file object."""
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
        """Extract this file to the given destination directory."""
        with closing(tarfile.open(self.tarfile_path, 'r')) as tarf:
            logger.info("Extracting {0} from {1} to {2}"
                        .format(self.filename, self.tarfile_path, dest_dir))
            tarf.extract(self.filename, dest_dir)

    def add_to_archive(self, tarf):
        """Copy this file into the given tarfile object."""
        self.open('r')
        try:
            logger.info("Copying {0} directly from {1} to TAR file"
                        .format(self.filename, self.tarfile_path))
            tarf.addfile(self.tarf.getmember(self.filename), self.obj)
        finally:
            self.close()
