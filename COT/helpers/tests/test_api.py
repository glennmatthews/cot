#!/usr/bin/env python
#
# tests_api.py - Unit test cases for COT.helpers.api module.
#
# April 2014, Glenn F. Matthews
# Copyright (c) 2014-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for COT.helpers.api module."""

import os
import logging

from distutils.version import StrictVersion

from COT.tests.ut import COT_UT
import COT.helpers.api
from COT.helpers import get_checksum
from COT.helpers import create_disk_image, convert_disk_image
from COT.helpers import get_disk_format, get_disk_capacity
from COT.helpers import HelperError, HelperNotFoundError

logger = logging.getLogger(__name__)


class TestGetChecksum(COT_UT):
    """Test cases for get_checksum() function."""

    def test_get_checksum_md5(self):
        """Test case for get_checksum() with md5 sum."""
        checksum = get_checksum(self.input_ovf, 'md5')
        self.assertEqual(checksum, "0a4aaf6b4a4e0c7808199cc3274c20ec")

        checksum = get_checksum(self.minimal_ovf, 'md5')
        self.assertEqual(checksum, "288e1e3fcb05265cd9b8c7578e173fef")

    def test_get_checksum_sha1(self):
        """Test case for get_checksum() with sha1 sum."""
        checksum = get_checksum(self.input_ovf, 'sha1')
        self.assertEqual(checksum,
                         "e4bb3f7b4d40447caea2b6c069c772c9a9d8fa48")

        checksum = get_checksum(self.minimal_ovf, 'sha1')
        self.assertEqual(checksum,
                         "5d0635163f6a580442f01466245e122f8412e8d6")

    def test_get_checksum_unsupported(self):
        """Test invalid options to get_checksum()."""
        self.assertRaises(NotImplementedError,
                          get_checksum,
                          self.input_ovf,
                          'sha256')
        self.assertRaises(NotImplementedError,
                          get_checksum,
                          self.input_ovf,
                          'crc')


class TestGetDiskFormat(COT_UT):
    """Test cases for get_disk_format() function."""

    def test_get_disk_format(self):
        """Get format and subformat of various disk images."""
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

        # Now a test that uses both qemu-img and file inspection
        try:
            (f, sf) = get_disk_format(self.blank_vmdk)
            self.assertEqual(f, 'vmdk')
            self.assertEqual(sf, 'streamOptimized')
        except HelperNotFoundError as e:
            self.fail(e.strerror)

    def test_get_disk_format_no_file(self):
        """Negative test - get_disk_format() for nonexistent file."""
        self.assertRaises(HelperError, get_disk_format, "")
        self.assertRaises(HelperError, get_disk_format, "/foo/bar/baz")


class TestConvertDiskImage(COT_UT):
    """Test cases for convert_disk_image()."""

    def test_convert_no_work_needed(self):
        """Convert a disk to its own format."""
        try:
            new_disk_path = convert_disk_image(self.blank_vmdk, self.temp_dir,
                                               'vmdk', 'streamOptimized')
            # No change -> don't create a new disk but just return existing.
            self.assertEqual(new_disk_path, self.blank_vmdk)
        except HelperNotFoundError as e:
            self.fail(e.strerror)

    def test_convert_to_vmdk_streamoptimized(self):
        """Convert a disk to vmdk streamOptimized sub-format."""
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

    def test_convert_to_vmdk_streamoptimized_old_qemu(self):
        """Code flow for old QEMU version."""
        COT.helpers.api.QEMUIMG._version = StrictVersion("1.0.0")
        try:
            temp_disk = os.path.join(self.temp_dir, "foo.qcow2")
            create_disk_image(temp_disk, capacity="16M")
            new_disk_path = convert_disk_image(temp_disk, self.temp_dir,
                                               'vmdk', 'streamOptimized')
            self.assertEqual(new_disk_path,
                             os.path.join(self.temp_dir, "foo.vmdk"))
            (f, sf) = get_disk_format(new_disk_path)
            self.assertEqual(f, 'vmdk')
            self.assertEqual(sf, 'streamOptimized')
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        finally:
            COT.helpers.api.QEMUIMG._version = None

    def test_convert_to_vmdk_streamoptimized_new_qemu(self):
        """Code flow for new QEMU version."""
        COT.helpers.api.QEMUIMG._version = StrictVersion("2.1.0")
        try:
            temp_disk = os.path.join(self.temp_dir, "foo.qcow2")
            create_disk_image(temp_disk, capacity="16M")
            new_disk_path = convert_disk_image(temp_disk, self.temp_dir,
                                               'vmdk', 'streamOptimized')
            self.assertEqual(new_disk_path,
                             os.path.join(self.temp_dir, 'foo.vmdk'))
            (f, sf) = get_disk_format(new_disk_path)
            self.assertEqual(f, 'vmdk')
            self.assertEqual(sf, 'streamOptimized')
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        finally:
            COT.helpers.api.QEMUIMG._version = None

    def test_convert_to_raw(self):
        """No support for converting VMDK to RAW at present."""
        self.assertRaises(NotImplementedError,
                          convert_disk_image,
                          self.blank_vmdk, self.temp_dir, 'raw', None)


class TestCreateDiskImage(COT_UT):
    """Test cases for create_disk_image()."""

    def test_create_invalid(self):
        """Invalid arguments."""
        # Must specify contents or capacity
        self.assertRaises(RuntimeError,
                          create_disk_image,
                          os.path.join(self.temp_dir, "out.iso"))
        # If extension not given, cannot guess file format
        self.assertRaises(RuntimeError,
                          create_disk_image,
                          os.path.join(self.temp_dir, "out"),
                          capacity="1M")
        # Trying to create a VHD format image, not currently possible
        self.assertRaises(HelperError,
                          create_disk_image,
                          os.path.join(self.temp_dir, "out.vhd"),
                          capacity="1M")
        self.assertRaises(HelperError,
                          create_disk_image,
                          os.path.join(self.temp_dir, "out.vmdk"),
                          file_format="vhd",
                          capacity="1M")
        # Don't know how to populate a qcow2 image with a file
        self.assertRaises(NotImplementedError,
                          create_disk_image,
                          os.path.join(self.temp_dir, "out.vmdk"),
                          file_format="qcow2",
                          contents=[self.input_ovf])

    def test_create_iso_with_contents(self):
        """Creation of ISO image containing files."""
        disk_path = os.path.join(self.temp_dir, "out.iso")
        try:
            create_disk_image(disk_path, contents=[self.input_ovf])
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        # TODO check ISO contents

    # Creation of empty disks is tested implicitly in other test classes
    # above - no need to repeat that here

    def test_create_raw_with_contents(self):
        """Creation of raw disk image containing files."""
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
