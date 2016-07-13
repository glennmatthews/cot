#!/usr/bin/env python
#
# test_qemu_img.py - Unit test cases for COT.helpers.qemu_img submodule.
#
# March 2015, Glenn F. Matthews
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

"""Unit test cases for the COT.helpers.qemu_img submodule."""

import os

from distutils.version import StrictVersion
import mock

from COT.helpers.tests.test_helper import HelperUT
from COT.helpers import HelperError
from COT.helpers.qemu_img import QEMUImg


class TestQEMUImg(HelperUT):
    """Test cases for QEMUImg helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = QEMUImg()
        super(TestQEMUImg, self).setUp()

    @mock.patch('COT.helpers.helper.Helper._check_output')
    def test_older_version(self, mock_check_output):
        """Test .version getter logic for older versions."""
        mock_check_output.return_value = """
qemu-img version 1.4.2, Copyright (c) 2004-2008 Fabrice Bellard
usage: qemu-img command [command options]
QEMU disk image utility

Command syntax:
..."""
        version = self.helper.version
        self.assertSubprocessCalls(mock_check_output,
                                   [['qemu-img', '--version']])
        self.assertEqual(version, StrictVersion("1.4.2"))

        # Output should be cached rather than re-invoking qemu-img
        mock_check_output.reset_mock()
        version = self.helper.version
        mock_check_output.assert_not_called()
        self.assertEqual(version, StrictVersion("1.4.2"))

    @mock.patch('COT.helpers.helper.Helper._check_output')
    def test_newer_version(self, mock_check_output):
        """Test .version getter logic for newer versions."""
        mock_check_output.return_value = \
            "qemu-img version 2.1.2, Copyright (c) 2004-2008 Fabrice Bellard"
        self.assertEqual(self.helper.version,
                         StrictVersion("2.1.2"))

    @mock.patch('COT.helpers.helper.Helper._check_output')
    def test_invalid_version(self, mock_check_output):
        """Negative test for .version getter logic."""
        mock_check_output.return_value = \
            "qemu-img: error: unknown argument --version"
        with self.assertRaises(RuntimeError):
            assert self.helper.version

    @mock.patch('subprocess.check_call')
    def test_install_helper_already_present(self, mock_check_call):
        """Do nothing when trying to re-install."""
        self.helper.install_helper()
        mock_check_call.assert_not_called()
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_apt_get(self):
        """Test installation via 'apt-get'."""
        self.apt_install_test('qemu-utils', 'qemu-img')

    def test_install_helper_port(self):
        """Test installation via 'port'."""
        self.port_install_test('qemu')

    def test_install_helper_yum(self):
        """Test installation via 'yum'."""
        self.yum_install_test('qemu-img')

    def test_get_disk_format(self):
        """Get format of various disk images."""
        self.assertEqual('vmdk', self.helper.get_disk_format(self.blank_vmdk))

        temp_disk = os.path.join(self.temp_dir, 'foo.img')
        self.helper.create_blank_disk(temp_disk, capacity="16M")
        self.assertEqual('raw', self.helper.get_disk_format(temp_disk))

        temp_disk = os.path.join(self.temp_dir, 'foo.qcow2')
        self.helper.create_blank_disk(temp_disk, capacity="1G")
        self.assertEqual('qcow2', self.helper.get_disk_format(temp_disk))

    def test_get_disk_format_no_file(self):
        """Negative test for get_disk_format() - no such file."""
        self.assertRaises(HelperError, self.helper.get_disk_format, "")
        self.assertRaises(HelperError, self.helper.get_disk_format,
                          "/foo/bar/baz")

    @mock.patch('COT.helpers.helper.Helper._check_output')
    def test_get_disk_format_not_available(self, mock_check_output):
        """Negative test for get_disk_format() - bad command output."""
        # Haven't found a way yet to make qemu-img actually fail here
        # without returning a non-zero RC and triggering a HelperError,
        # so we'll have to fake it
        mock_check_output.return_value = "qemu-img info: unsupported command"
        self.assertRaises(RuntimeError, self.helper.get_disk_format,
                          "/foo/bar")

    def test_get_disk_capacity(self):
        """Test the get_disk_capacity() method."""
        self.assertEqual("536870912",
                         self.helper.get_disk_capacity(self.blank_vmdk))

        self.assertEqual("1073741824",
                         self.helper.get_disk_capacity(self.input_vmdk))

    def test_get_disk_capacity_no_file(self):
        """Negative test for get_disk_capacity() - no such file."""
        self.assertRaises(HelperError, self.helper.get_disk_capacity, "")
        self.assertRaises(HelperError, self.helper.get_disk_capacity,
                          "/foo/bar/baz")

    @mock.patch('COT.helpers.helper.Helper._check_output')
    def test_get_disk_capacity_not_available(self, mock_check_output):
        """Negative test for get_disk_capacity() - bad command output."""
        # Haven't found a way yet to make qemu-img actually fail here
        # without returning a non-zero RC and triggering a HelperError,
        # so we'll have to fake it
        mock_check_output.return_value = "qemu-img info: unsupported command"
        self.assertRaises(RuntimeError, self.helper.get_disk_capacity,
                          "/foo/bar")

    def test_create_invalid(self):
        """Invalid arguments."""
        # If extension not given, cannot guess file format
        self.assertRaises(RuntimeError,
                          self.helper.create_blank_disk,
                          os.path.join(self.temp_dir, "out"),
                          capacity="1M")

    def test_convert_unsupported(self):
        """Negative test for convert_disk_image() - unsupported formats."""
        with self.assertRaises(NotImplementedError):
            self.helper.convert_disk_image(self.blank_vmdk, self.temp_dir,
                                           'vhd')
        self.set_helper_version(StrictVersion("2.0.99"))
        with self.assertRaises(NotImplementedError):
            self.helper.convert_disk_image(self.blank_vmdk, self.temp_dir,
                                           'vmdk', 'streamOptimized')
