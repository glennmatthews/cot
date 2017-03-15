#!/usr/bin/env python
#
# March 2017, Glenn F. Matthews
# Copyright (c) 2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for COT.utilities module."""

import errno
import os

from COT.tests import COTTestCase
import COT.utilities
from COT.disks.raw import RAW


class TestUtilities(COTTestCase):
    """Test cases for COT.utilities module."""

    def test_available_bytes_at_path_errors(self):
        """Negative test for available_bytes_at_path."""
        self.assertRaises(OSError,
                          COT.utilities.available_bytes_at_path,
                          "/bar/foo")

    def test_directory_size_bad_path(self):
        """Negative tests for directory_size() function."""
        with self.assertRaises(OSError) as catcher:
            COT.utilities.directory_size("/bar/foo")
        self.assertEqual(catcher.exception.errno, errno.ENOENT)

        with self.assertRaises(OSError) as catcher:
            COT.utilities.directory_size(__file__)
        self.assertEqual(catcher.exception.errno, errno.ENOTDIR)

    def test_directory_size_continuation(self):
        """Directory size calculation needs to continue even if files fail."""
        # Valid file
        RAW.create_file(os.path.join(self.temp_dir, "1.raw"), capacity="128K")
        # Invalid symlink
        os.symlink("/foo/bar", os.path.join(self.temp_dir, "2.raw"))
        # Valid file
        RAW.create_file(os.path.join(self.temp_dir, "3.raw"), capacity="128K")

        self.assertEqual(COT.utilities.directory_size(self.temp_dir),
                         256 << 10)
