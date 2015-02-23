#!/usr/bin/env python
#
# helpers.py - Unit test cases for COT.helpers submodule.
#
# February 2015, Glenn F. Matthews
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

from COT.tests.ut import COT_UT
from COT.helpers.helper import Helper, HelperError, HelperNotFoundError
from COT.helpers.ovftool import OVFTool
from COT.helpers.qemu_img import QEMUImg

logger = logging.getLogger(__name__)


class HelpersUT(COT_UT):
    """Generic class for testing Helpers and subclasses thereof."""

    def stub_check_call(self, argv, require_success=True):
        logger.info("stub_check_call({0}, {1})"
                    .format(argv, require_success))
        self.last_argv = argv

    def stub_check_output(self, argv, require_success=True):
        logger.info("stub_check_output({0}, {1})"
                    .format(argv, require_success))
        self.last_argv = argv
        if self.fake_output:
            return self.fake_output
        return self._check_output(argv, require_success)

    def setUp(self):
        # subclass needs to set self.helper
        super(HelpersUT, self).setUp()
        self.match_argv = None
        self.fake_output = None
        self.last_argv = None
        self._check_call = self.helper._check_call
        self.helper._check_call = self.stub_check_call
        self._check_output = self.helper._check_output
        self.helper._check_output = self.stub_check_output

    def tearDown(self):
        self.helper._check_call = self._check_call
        self.helper._check_output = self._check_output
        super(HelpersUT, self).tearDown()


class HelperGenericTest(COT_UT):
    """Test cases for generic Helpers class."""

    def setUp(self):
        self.helper = Helper("generic")
        super(HelperGenericTest, self).setUp()

    def test_check_call_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist"""
        self.assertRaises(HelperNotFoundError,
                          self.helper._check_call, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          self.helper._check_call,
                          ["not_a_command"], require_success=True)

    def test_check_call_helpererror(self):
        """HelperError if executable fails and require_success is set"""

        with self.assertRaises(HelperError) as cm:
            self.helper._check_call(["false"])
        self.assertEqual(cm.exception.errno, 1)

        self.helper._check_call(["false"], require_success=False)

    def test_check_output_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist"""
        self.assertRaises(HelperNotFoundError,
                          self.helper._check_output, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          self.helper._check_output, ["not_a_command"],
                          require_success=True)

    def test_check_output_helpererror(self):
        """HelperError if executable fails and require_success is set"""

        with self.assertRaises(HelperError) as cm:
            self.helper._check_output(["false"])
        self.assertEqual(cm.exception.errno, 1)

        self.helper._check_output(["false"], require_success=False)


class TestOVFTool(HelpersUT):
    """Test cases for OVFTool helper class."""

    def setUp(self):
        self.helper = OVFTool()
        super(TestOVFTool, self).setUp()

    def test_invalid_version(self):
        self.fake_output = "Error: Unknown option: 'version'"
        with self.assertRaises(AttributeError):
            self.helper.version


class TestQEMUImg(HelpersUT):
    """Test cases for QEMUImg helper class."""

    def setUp(self):
        self.helper = QEMUImg()
        super(TestQEMUImg, self).setUp()

    def test_older_version(self):
        self.fake_output = """
qemu-img version 1.4.2, Copyright (c) 2004-2008 Fabrice Bellard
usage: qemu-img command [command options]
QEMU disk image utility

Command syntax:
..."""
        version = self.helper.version
        self.assertEqual(self.last_argv, ['qemu-img', '--version'])
        self.assertEqual(version, StrictVersion("1.4.2"))

        # Output should be cached rather than re-invoking qemu-img
        self.last_argv = None
        self.fake_output = "Gotcha!"
        version = self.helper.version
        self.assertEqual(self.last_argv, None)
        self.assertEqual(version, StrictVersion("1.4.2"))

    def test_newer_version(self):
        self.fake_output = \
            "qemu-img version 2.1.2, Copyright (c) 2004-2008 Fabrice Bellard"
        self.assertEqual(self.helper.version,
                         StrictVersion("2.1.2"))

    def test_invalid_version(self):
        self.fake_output = "qemu-img: error: unknown argument --version"
        with self.assertRaises(AttributeError):
            self.helper.version

    def test_get_disk_format(self):
        """Get format of various disk images."""
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        self.assertEqual('vmdk', self.helper.get_disk_format(disk_path))

        temp_disk = os.path.join(self.temp_dir, 'foo.img')
        self.helper.create_blank_disk(temp_disk, capacity="16M")
        self.assertEqual('raw', self.helper.get_disk_format(temp_disk))

        temp_disk = os.path.join(self.temp_dir, 'foo.qcow2')
        self.helper.create_blank_disk(temp_disk, capacity="1G")
        self.assertEqual('qcow2', self.helper.get_disk_format(temp_disk))

    def test_get_disk_format_no_file(self):
        self.assertRaises(HelperError, self.helper.get_disk_format, "")
        self.assertRaises(HelperError, self.helper.get_disk_format,
                          "/foo/bar/baz")

    def test_get_disk_format_not_available(self):
        # Haven't found a way yet to make qemu-img actually fail here
        # without returning a non-zero RC and triggering a HelperError,
        # so we'll have to fake it
        self.fake_output = "qemu-img info: unsupported command"
        self.assertRaises(RuntimeError, self.helper.get_disk_format,
                          "/foo/bar")

    def test_get_disk_capacity(self):
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        self.assertEqual("536870912",
                         self.helper.get_disk_capacity(disk_path))

        disk_path = os.path.join(os.path.dirname(__file__), "input.vmdk")
        self.assertEqual("1073741824",
                         self.helper.get_disk_capacity(disk_path))

    def test_get_disk_capacity_no_file(self):
        self.assertRaises(HelperError, self.helper.get_disk_capacity, "")
        self.assertRaises(HelperError, self.helper.get_disk_capacity,
                          "/foo/bar/baz")

    def test_get_disk_capacity_not_available(self):
        # Haven't found a way yet to make qemu-img actually fail here
        # without returning a non-zero RC and triggering a HelperError,
        # so we'll have to fake it
        self.fake_output = "qemu-img info: unsupported command"
        self.assertRaises(RuntimeError, self.helper.get_disk_capacity,
                          "/foo/bar")
