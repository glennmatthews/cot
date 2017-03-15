#!/usr/bin/env python
#
# test_disk.py - Unit test cases for DiskRepresentation class.
#
# October 2016, Glenn F. Matthews
# Copyright (c) 2014-2017 the COT project developers.
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

from COT.tests import COTTestCase
from COT.disks import DiskRepresentation
from COT.helpers import helpers, HelperError

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc


class TestDiskRepresentation(COTTestCase):
    """Test DiskRepresentation class."""

    def test_disk_representation_from_file_raw(self):
        """Test if DiskRepresentation.from_file() works for raw images."""
        temp_disk = os.path.join(self.temp_dir, 'foo.img')
        helpers['qemu-img'].call(['create', '-f', 'raw', temp_disk, "16M"])
        diskrep = DiskRepresentation.from_file(temp_disk)
        self.assertEqual(diskrep.disk_format, "raw")
        self.assertEqual(diskrep.disk_subformat, None)

    def test_disk_representation_from_file_qcow2(self):
        """Test if DiskRepresentation.from_file() works for qcow2 images."""
        temp_disk = os.path.join(self.temp_dir, 'foo.qcow2')
        helpers['qemu-img'].call(['create', '-f', 'qcow2', temp_disk, "16M"])
        diskrep = DiskRepresentation.from_file(temp_disk)
        self.assertEqual(diskrep.disk_format, "qcow2")
        self.assertEqual(diskrep.disk_subformat, None)

    def test_disk_representation_from_file_vmdk(self):
        """Test if DiskRepresentation.from_file() works for vmdk images."""
        diskrep = DiskRepresentation.from_file(self.blank_vmdk)
        self.assertEqual(diskrep.disk_format, "vmdk")
        self.assertEqual(diskrep.disk_subformat, "streamOptimized")

    def test_disk_representation_from_file_iso(self):
        """Test if DiskRepresentation.from_file() works for iso images."""
        diskrep = DiskRepresentation.from_file(self.input_iso)
        self.assertEqual(diskrep.disk_format, "iso")
        # In Travis CI we can't currently install isoinfo (via genisoimage).
        # https://github.com/travis-ci/apt-package-whitelist/issues/588
        if helpers['isoinfo']:
            self.assertEqual(diskrep.disk_subformat, "")

    def test_disk_representation_from_file_errors(self):
        """Check DiskRepresentation.from_file() error handling."""
        self.assertRaises(IOError, DiskRepresentation.from_file,
                          "")
        self.assertRaises(IOError, DiskRepresentation.from_file,
                          "/foo/bar/baz")
        self.assertRaises(TypeError, DiskRepresentation.from_file,
                          None)
        with mock.patch('COT.helpers.helper.check_output') as mock_co:
            mock_co.return_value = "qemu-img info: unsupported command"
            self.assertRaises(RuntimeError,
                              DiskRepresentation.from_file,
                              self.input_vmdk)
        # We support QCOW2 but not QCOW at present
        temp_path = os.path.join(self.temp_dir, "foo.qcow")
        helpers['qemu-img'].call(['create', '-f', 'qcow', temp_path, '8M'])
        self.assertRaises(NotImplementedError,
                          DiskRepresentation.from_file, temp_path)

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

    def test_for_new_file_errors(self):
        """Invalid inputs to for_new_file()."""
        # No support for VHD format at present
        self.assertRaises(NotImplementedError,
                          DiskRepresentation.for_new_file,
                          path=os.path.join(self.temp_dir, "foo.vhd"),
                          disk_format="vhd",
                          capacity="1M")

    def test_create_file_path_mandatory(self):
        """Can't create a file without specifying a path."""
        self.assertRaises(ValueError,
                          DiskRepresentation.create_file, path=None)

    def test_create_file_already_extant(self):
        """Can't call create_file if the file already exists."""
        self.assertRaises(RuntimeError,
                          DiskRepresentation.create_file,
                          path=self.blank_vmdk)

    def test_create_file_insufficient_info(self):
        """Can't create a file with neither files nor capacity."""
        self.assertRaises(RuntimeError,
                          DiskRepresentation.create_file,
                          path=os.path.join(self.temp_dir, "foo"))

    def test_convert_to_errors(self):
        """Invalid inputs to convert_to()."""
        self.assertRaises(
            NotImplementedError,
            DiskRepresentation.from_file(self.blank_vmdk).convert_to,
            "frobozz", self.temp_dir)
