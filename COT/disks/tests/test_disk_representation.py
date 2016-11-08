#!/usr/bin/env python
#
# test_disk.py - Unit test cases for DiskRepresentation class.
#
# October 2016, Glenn F. Matthews
# Copyright (c) 2014-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for DiskRepresentation class."""

import logging
import os
import mock

from COT.tests.ut import COT_UT
from COT.disks.disk import DiskRepresentation
from COT.helpers import HelperError

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc


class TestDisk(COT_UT):
    """Test Disk class."""

    @mock.patch('COT.helpers.helper.check_output')
    def test_capacity_qemu_error(self, mock_check_output):
        """Test error handline if qemu-img reports an error."""
        mock_check_output.return_value = "qemu-img info: unsupported command"
        with self.assertRaises(RuntimeError):
            assert DiskRepresentation(path=self.blank_vmdk).capacity

    def test_from_other_image(self):
        """No default from_other_image logic."""
        self.assertRaises(NotImplementedError,
                          DiskRepresentation.from_other_image,
                          self.blank_vmdk, self.temp_dir)

    def test_files(self):
        """No default files getter logic."""
        with self.assertRaises(NotImplementedError):
            assert DiskRepresentation(path=self.blank_vmdk).files

    def test_file_is_this_type_missing_file(self):
        """file_is_this_type raises an error if file doesn't exist."""
        self.assertRaises(HelperError,
                          DiskRepresentation.file_is_this_type, "/foo/bar")

    def test_create_file_path_mandatory(self):
        """Can't create a file without specifying a path."""
        self.assertRaises(ValueError, DiskRepresentation, path=None)

    def test_create_file_already_extant(self):
        """Can't call create_file if the file already exists."""
        self.assertRaises(RuntimeError,
                          DiskRepresentation(path=self.blank_vmdk).create_file)

    def test_create_file_insufficient_info(self):
        """Can't create a file with neither files nor capacity."""
        self.assertRaises(RuntimeError,
                          DiskRepresentation,
                          path=os.path.join(self.temp_dir, "foo"))
