#!/usr/bin/env python
#
# helper_tools.py - Unit test cases for helper tools module.
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

import os
import logging

from distutils.version import StrictVersion
from verboselogs import VerboseLogger

logging.setLoggerClass(VerboseLogger)
logger = logging.getLogger(__name__)

from COT.data_validation import ValueUnsupportedError
import COT.helper_tools
from COT.helper_tools import get_checksum
from COT.helper_tools import create_disk_image, convert_disk_image
from COT.helper_tools import get_disk_format, get_disk_capacity
from COT.helper_tools import HelperError, HelperNotFoundError
from COT.tests.ut import COT_UT


class HelperToolsUT(COT_UT):
    """Generic class for testing helper tools methods"""

    def stub_check_call(self, argv, require_success=True):
        logger.info("stub_check_call({0}, {1})"
                    .format(argv, require_success))
        if self.match_argv:
            found_match = True
            for a, b in zip(self.match_argv, argv):
                if a != b:
                    found_match = False
                    break
            if found_match:
                self.last_argv = argv
                logger.info("Caught call to {0}: {1}"
                            .format(" ".join(self.match_argv),
                                    " ".join(argv)))
                return
        return self._check_call(argv, require_success)

    def stub_check_output(self, argv, require_success=True):
        logger.info("stub_check_output({0}, {1})"
                    .format(argv, require_success))
        if self.match_argv:
            found_match = True
            for a, b in zip(self.match_argv, argv):
                if a != b:
                    found_match = False
                    break
            if found_match:
                self.last_argv = argv
                logger.info("Caught call to {0}: {1}"
                            .format(" ".join(self.match_argv),
                                    " ".join(argv)))
                return self.fake_output
        return self._check_output(argv, require_success)

    def setUp(self):
        super(HelperToolsUT, self).setUp()
        self.match_argv = None
        self.fake_output = None
        self.last_argv = None
        self._check_call = COT.helper_tools.check_call
        COT.helper_tools.check_call = self.stub_check_call
        self._check_output = COT.helper_tools.check_output
        COT.helper_tools.check_output = self.stub_check_output

    def tearDown(self):
        COT.helper_tools.check_call = self._check_call
        COT.helper_tools.check_output = self._check_output
        super(HelperToolsUT, self).tearDown()


class TestCheckCall(COT_UT):
    """Test cases for check_call() function"""

    def test_check_call_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist"""
        self.assertRaises(HelperNotFoundError,
                          COT.helper_tools.check_call, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          COT.helper_tools.check_call,
                          ["not_a_command"], require_success=True)

    def test_check_call_helpererror(self):
        """HelperError if executable fails and require_success is set"""

        with self.assertRaises(HelperError) as cm:
            COT.helper_tools.check_call(["false"])
        self.assertEqual(cm.exception.errno, 1)

        COT.helper_tools.check_call(["false"], require_success=False)


class TestCheckOutput(COT_UT):
    """Test cases for check_output() function"""

    def test_check_output_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist"""
        self.assertRaises(HelperNotFoundError,
                          COT.helper_tools.check_output, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          COT.helper_tools.check_output, ["not_a_command"],
                          require_success=True)

    def test_check_output_helpererror(self):
        """HelperError if executable fails and require_success is set"""

        with self.assertRaises(HelperError) as cm:
            COT.helper_tools.check_output(["false"])
        self.assertEqual(cm.exception.errno, 1)

        COT.helper_tools.check_output(["false"], require_success=False)


class TestGetChecksum(COT_UT):
    """Test cases for get_checksum() function"""

    def test_get_checksum_md5(self):
        """Test case for get_checksum() with md5 sum."""
        try:
            checksum = get_checksum(self.input_ovf, 'md5')
            self.assertEqual(checksum, "5aa4e3defb16e02ea16dd07cff77bfdf")

            checksum = get_checksum(self.minimal_ovf, 'md5')
            self.assertEqual(checksum, "288e1e3fcb05265cd9b8c7578e173fef")
        except HelperNotFoundError as e:
            self.fail(e.strerror)

    def test_get_checksum_sha1(self):
        """Test case for get_checksum() with sha1 sum."""
        try:
            checksum = get_checksum(self.input_ovf, 'sha1')
            self.assertEqual(checksum,
                             "63b6c9d71cc8b051ffbfa8d1d630d30a2dfb9701")

            checksum = get_checksum(self.minimal_ovf, 'sha1')
            self.assertEqual(checksum,
                             "5d0635163f6a580442f01466245e122f8412e8d6")
        except HelperNotFoundError as e:
            self.fail(e.strerror)

    def test_get_checksum_unsupported(self):
        """Test invalid options to get_checksum()."""

        self.assertRaises(ValueUnsupportedError,
                          get_checksum,
                          self.input_ovf,
                          'sha256')
        self.assertRaises(ValueUnsupportedError,
                          get_checksum,
                          self.input_ovf,
                          'crc')


class TestGetQEMUImgVersion(HelperToolsUT):
    """Test cases for get_qemu_img_version() function"""

    def setUp(self):
        super(TestGetQEMUImgVersion, self).setUp()
        COT.helper_tools.QEMU_IMG_VERSION = None
        self.match_argv = ['qemu-img', '--version']

    def tearDown(self):
        COT.helper_tools.QEMU_IMG_VERSION = None
        super(TestGetQEMUImgVersion, self).tearDown()

    def test_older_version(self):
        self.fake_output = """
qemu-img version 1.4.2, Copyright (c) 2004-2008 Fabrice Bellard
usage: qemu-img command [command options]
QEMU disk image utility

Command syntax:
..."""
        version = COT.helper_tools.get_qemu_img_version()
        self.assertEqual(self.match_argv, self.last_argv)
        self.assertEqual(version, StrictVersion("1.4.2"))

        # Output should be cached rather than re-invoking qemu-img
        self.last_argv = None
        self.fake_output = "Gotcha!"
        version = COT.helper_tools.get_qemu_img_version()
        self.assertEqual(self.last_argv, None)
        self.assertEqual(version, StrictVersion("1.4.2"))

    def test_newer_version(self):
        self.fake_output = \
            "qemu-img version 2.1.2, Copyright (c) 2004-2008 Fabrice Bellard"
        self.assertEqual(COT.helper_tools.get_qemu_img_version(),
                         StrictVersion("2.1.2"))

    def test_invalid_version(self):
        self.fake_output = "qemu-img: error: unknown argument --version"
        self.assertRaises(RuntimeError,
                          COT.helper_tools.get_qemu_img_version)


class TestGetDiskFormat(HelperToolsUT):
    """Test cases for get_disk_format() function"""

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
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        try:
            (f, sf) = get_disk_format(disk_path)
            self.assertEqual(f, 'vmdk')
            self.assertEqual(sf, 'streamOptimized')
        except HelperNotFoundError as e:
            self.fail(e.strerror)

    def test_get_disk_format_no_file(self):
        self.assertRaises(HelperError, get_disk_format, "")
        self.assertRaises(HelperError, get_disk_format, "/foo/bar/baz")

    def test_get_disk_format_not_available(self):
        # Haven't found a way yet to make qemu-img actually fail here
        # without returning a non-zero RC and triggering a HelperError,
        # so we'll have to fake it
        self.match_argv = ['qemu-img', 'info']
        self.fake_output = "qemu-img info: unsupported command"
        self.assertRaises(RuntimeError, get_disk_format, "/foo/bar")


class TestGetDiskCapacity(HelperToolsUT):
    """Test cases for get_disk_capacity()."""

    def test_get_disk_capacity(self):
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        try:
            capacity = get_disk_capacity(disk_path)
            self.assertEqual(capacity, "536870912")
        except HelperNotFoundError as e:
            self.fail(e.strerror)

        disk_path = os.path.join(os.path.dirname(__file__), "input.vmdk")
        capacity = get_disk_capacity(disk_path)
        self.assertEqual(capacity, "1073741824")

    def test_get_disk_format_no_file(self):
        self.assertRaises(HelperError, get_disk_capacity, "")
        self.assertRaises(HelperError, get_disk_capacity, "/foo/bar/baz")

    def test_get_disk_format_not_available(self):
        # Haven't found a way yet to make qemu-img actually fail here
        # without returning a non-zero RC and triggering a HelperError,
        # so we'll have to fake it
        self.match_argv = ['qemu-img', 'info']
        self.fake_output = "qemu-img info: unsupported command"
        self.assertRaises(RuntimeError, get_disk_capacity, "/foo/bar")


class TestConvertDiskImage(HelperToolsUT):
    """Test cases for convert_disk_image()."""

    def test_convert_no_work_needed(self):
        """Convert a disk to its own format."""
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

    def test_convert_to_vmdk_streamoptimized_old_qemu(self):
        """Code flow for old QEMU version"""
        COT.helper_tools.QEMU_IMG_VERSION = StrictVersion("1.0.0")
        self.match_argv = ['vmdktool']
        try:
            temp_disk = os.path.join(self.temp_dir, "foo.qcow2")
            create_disk_image(temp_disk, capacity="16M")
            new_disk_path = convert_disk_image(temp_disk, self.temp_dir,
                                               'vmdk', 'streamOptimized')
            # convert_disk_image will use qemu to convert qcow2 to img
            self.assertEqual(self.last_argv,
                             ['vmdktool', '-z9', '-v',
                              os.path.join(self.temp_dir, 'foo.vmdk'),
                              os.path.join(self.temp_dir, 'foo.img')])
            self.assertEqual(new_disk_path,
                             os.path.join(self.temp_dir, "foo.vmdk"))
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        finally:
            COT.helper_tools.QEMU_IMG_VERSION = None

    def test_convert_to_vmdk_streamoptimized_new_qemu(self):
        """Code flow for new QEMU version"""
        COT.helper_tools.QEMU_IMG_VERSION = StrictVersion("2.1.0")
        self.match_argv = ['qemu-img', 'convert']
        try:
            temp_disk = os.path.join(self.temp_dir, "foo.qcow2")
            create_disk_image(temp_disk, capacity="16M")
            new_disk_path = convert_disk_image(temp_disk, self.temp_dir,
                                               'vmdk', 'streamOptimized')
            self.assertEqual(self.last_argv,
                             ['qemu-img', 'convert', '-O', 'vmdk',
                              '-o', 'subformat=streamOptimized', temp_disk,
                              new_disk_path])
            self.assertEqual(new_disk_path,
                             os.path.join(self.temp_dir, 'foo.vmdk'))
        except HelperNotFoundError as e:
            self.fail(e.strerror)
        finally:
            COT.helper_tools.QEMU_IMG_VERSION = None

    def test_convert_to_raw(self):
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        self.assertRaises(ValueUnsupportedError,
                          convert_disk_image,
                          disk_path, self.temp_dir, 'raw', None)


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
        self.assertRaises(ValueUnsupportedError,
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


class TestGetOvftoolVersion(HelperToolsUT):
    """Test cases for get_ovftool_version() function"""

    def setUp(self):
        super(TestGetOvftoolVersion, self).setUp()
        COT.helper_tools.OVFTOOL_VERSION = None
        self.match_argv = ['ovftool', '--version']

    def tearDown(self):
        COT.helper_tools.OVFTOOL_VERSION = None
        super(TestGetOvftoolVersion, self).tearDown()

    def test_invalid_version(self):
        self.fake_output = "Error: Unknown option: 'version'"
        self.assertRaises(RuntimeError,
                          COT.helper_tools.get_ovftool_version)
