#!/usr/bin/env python
#
# test_api.py - Unit test cases for public API of COT.disks module.
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

"""Unit test cases for public API of COT.disks module."""

import os
import logging
import mock

from COT.tests.ut import COT_UT
from COT.helpers import helpers
import COT.disks

logger = logging.getLogger(__name__)


class TestDiskAPI(COT_UT):
    """Test public API of COT.disks module."""

    def test_create_disk_errors(self):
        """Invalid inputs to create_disk()."""
        # No support for VHD format at present
        self.assertRaises(NotImplementedError,
                          COT.disks.create_disk, 'vhd', capacity="1M")

    def test_disk_representation_from_file_raw(self):
        """Test if disk_representation_from_file() works for raw images."""
        temp_disk = os.path.join(self.temp_dir, 'foo.img')
        helpers['qemu-img'].call(['create', '-f', 'raw', temp_disk, "16M"])
        dr = COT.disks.disk_representation_from_file(temp_disk)
        self.assertEqual(dr.disk_format, "raw")
        self.assertEqual(dr.disk_subformat, None)

    def test_disk_representation_from_file_qcow2(self):
        """Test if disk_representation_from_file() works for qcow2 images."""
        temp_disk = os.path.join(self.temp_dir, 'foo.qcow2')
        helpers['qemu-img'].call(['create', '-f', 'qcow2', temp_disk, "16M"])
        dr = COT.disks.disk_representation_from_file(temp_disk)
        self.assertEqual(dr.disk_format, "qcow2")
        self.assertEqual(dr.disk_subformat, None)

    def test_disk_representation_from_file_vmdk(self):
        """Test if disk_representation_from_file() works for vmdk images."""
        dr = COT.disks.disk_representation_from_file(self.blank_vmdk)
        self.assertEqual(dr.disk_format, "vmdk")
        self.assertEqual(dr.disk_subformat, "streamOptimized")

    def test_disk_representation_from_file_iso(self):
        """Test if disk_representation_from_file() works for iso images."""
        dr = COT.disks.disk_representation_from_file(self.input_iso)
        self.assertEqual(dr.disk_format, "iso")
        # In Travis CI we can't currently install isoinfo (via genisoimage).
        # https://github.com/travis-ci/apt-package-whitelist/issues/588
        if helpers['isoinfo']:
            self.assertEqual(dr.disk_subformat, "")

    def test_disk_representation_from_file_errors(self):
        """Check disk_representation_from_file() error handling."""
        self.assertRaises(IOError, COT.disks.disk_representation_from_file,
                          "")
        self.assertRaises(IOError, COT.disks.disk_representation_from_file,
                          "/foo/bar/baz")
        self.assertRaises(TypeError, COT.disks.disk_representation_from_file,
                          None)
        with mock.patch('COT.helpers.helper.check_output') as mock_co:
            mock_co.return_value = "qemu-img info: unsupported command"
            self.assertRaises(RuntimeError,
                              COT.disks.disk_representation_from_file,
                              self.input_vmdk)
        # We support QCOW2 but not QCOW at present
        temp_path = os.path.join(self.temp_dir, "foo.qcow")
        helpers['qemu-img'].call(['create', '-f', 'qcow', temp_path, '8M'])
        self.assertRaises(NotImplementedError,
                          COT.disks.disk_representation_from_file, temp_path)

    def test_convert_disk_errors(self):
        """Invalid inputs to convert_disk()."""
        self.assertRaises(
            NotImplementedError, COT.disks.convert_disk,
            COT.disks.disk_representation_from_file(self.blank_vmdk),
            self.temp_dir, "frobozz")
