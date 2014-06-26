#!/usr/bin/env python
#
# helper_tools.py - Unit test cases for helper tools module.
#
# April 2014, Glenn F. Matthews
# Copyright (c) 2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

import os
import shutil
import tempfile
import unittest

from COT.data_validation import ValueUnsupportedError
from COT.helper_tools import *
from COT.tests.ut import COT_UT

class TestGetChecksum(COT_UT):
    """Test cases for get_checksum() function"""

    def test_get_checksum_md5(self):
        """Test case for get_checksum() with md5 sum.
        """
        try:
            checksum = get_checksum(self.input_ovf, 'md5')
            self.assertEqual(checksum, "1318e8d525aab8113af95a0d2d4b8858")

            checksum = get_checksum(self.minimal_ovf, 'md5')
            self.assertEqual(checksum, "288e1e3fcb05265cd9b8c7578e173fef")
        except HelperNotFoundError as e:
            self.fail(e.strerror)

    def test_get_checksum_sha1(self):
        """Test case for get_checksum() with sha1 sum.
        """
        try:
            checksum = get_checksum(self.input_ovf, 'sha1')
            self.assertEqual(checksum,
                             "6add403901f5aebaa68c9c51078e510a745ae912")

            checksum = get_checksum(self.minimal_ovf, 'sha1')
            self.assertEqual(checksum,
                             "5d0635163f6a580442f01466245e122f8412e8d6")
        except HelperNotFoundError as e:
            self.fail(e.strerror)


    def test_get_checksum_unsupported(self):
        """Test invalid options to get_checksum().
        """

        self.assertRaises(ValueUnsupportedError,
                          get_checksum,
                          self.input_ovf,
                          'sha256')
        self.assertRaises(ValueUnsupportedError,
                          get_checksum,
                          self.input_ovf,
                          'crc')

class TestGetDiskFormat(COT_UT):
    """Test cases for get_disk_format() function"""

    def test_get_disk_format(self):
        """TODO
        """
        # First, tests that just use qemu-img
        try:
            temp_disk = os.path.join(self.temp_dir, 'foo.img')
            create_disk_image(temp_disk, capacity="16M")
            (f, sf) = get_disk_format(temp_disk)
            self.assertEqual(f, 'raw')
            self.assertEqual(sf, None)

            temp_disk = os.path.join(self.temp_dir, 'foo.qcow2')
            create_disk_image(temp_disk, capacity="1G")
            (f, sf) = get_disk_format(temp_disk)
            self.assertEqual(f, 'qcow2')
            self.assertEqual(sf, None)
        except HelperNotFoundError as e:
            self.fail(e.strerror)

        # Now a test that uses both qemu-img and vmdktool
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        try:
            (f, sf) = get_disk_format(disk_path)
            self.assertEqual(f, 'vmdk')
            self.assertEqual(sf, 'streamOptimized')
        except HelperNotFoundError as e:
            self.fail(e.strerror)


class TestGetDiskCapacity(COT_UT):
    """Test cases for get_disk_capacity().
    """

    def test_get_disk_capacity(self):
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        try:
            capacity = get_disk_capacity(disk_path)
            self.assertEqual(capacity, "8589934592")
        except HelperNotFoundError as e:
            self.fail(e.strerror)

class TestConvertDiskImage(COT_UT):
    """Test cases for convert_disk_image().
    """

    def test_convert_no_work_needed(self):
        """Convert a disk to its own format.
        """
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        try:
            new_disk_path = convert_disk_image(disk_path, self.temp_dir,
                                               'vmdk', 'streamOptimized')
            # No change -> don't create a new disk but just return existing.
            self.assertEqual(new_disk_path, disk_path)
        except HelperNotFoundError as e:
            self.fail(e.strerror)

    def test_convert_to_vmdk_streamoptimized(self):
        """Convert a disk to vmdk streamOptimized sub-format"""

        # Raw to stream-optimized vmdk
        temp_disk = os.path.join(self.temp_dir, "foo.img")
        try:
            create_disk_image(temp_disk, capacity="16M")
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        try:
            new_disk_path = convert_disk_image(temp_disk, self.temp_dir,
                                               'vmdk', 'streamOptimized')
        except HelperNotFoundError as e:
            self.fail(e.strerror)

        (f, sf) = get_disk_format(new_disk_path)
        self.assertEqual(f, 'vmdk')
        self.assertEqual(sf, 'streamOptimized')

        # Non-stream-optimized to stream-optimized
        temp_disk = os.path.join(self.temp_dir, "foo.vmdk")
        create_disk_image(temp_disk, capacity="16M")
        new_disk_path = convert_disk_image(temp_disk, self.temp_dir,
                                           'vmdk', 'streamOptimized')
        (f, sf) = get_disk_format(new_disk_path)
        self.assertEqual(f, 'vmdk')
        self.assertEqual(sf, 'streamOptimized')


class TestCreateDiskImage(COT_UT):
    """Test cases for create_disk_image().
    """

    def test_create_iso_with_contents(self):
        """Creation of ISO image containing files.
        """
        disk_path = os.path.join(self.temp_dir, "out.iso")
        try:
            create_disk_image(disk_path, contents=[self.input_ovf])
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        # TODO check ISO contents

    # Creation of empty disks is tested implicitly in other test classes
    # above - no need to repeat that here

    def test_create_raw_with_contents(self):
        """Creation of raw disk image containing files.
        """
        disk_path = os.path.join(self.temp_dir, "out.img")
        try:
            create_disk_image(disk_path, contents=[self.input_ovf])
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        (f, sf) = get_disk_format(disk_path)
        self.assertEqual(f, 'raw')
        try:
            capacity = get_disk_capacity(disk_path)
            self.assertEqual(capacity, "8388608")
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        # TODO check raw file contents

        # Again, but now force the disk size
        try:
            create_disk_image(disk_path, contents=[self.input_ovf],
                              capacity="64M")
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        (f, sf) = get_disk_format(disk_path)
        self.assertEqual(f, 'raw')
        try:
            capacity = get_disk_capacity(disk_path)
            self.assertEqual(capacity, "67108864")
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        # TODO check raw file contents
