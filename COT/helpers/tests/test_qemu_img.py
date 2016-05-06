#!/usr/bin/env python
#
# test_qemu_img.py - Unit test cases for COT.helpers.qemu_img submodule.
#
# March 2015, Glenn F. Matthews
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

"""Unit test cases for the COT.helpers.qemu_img submodule."""

import os

from distutils.version import StrictVersion

from .test_helper import HelperUT
from COT.helpers import HelperError
from COT.helpers.helper import Helper
from COT.helpers.qemu_img import QEMUImg


class TestQEMUImg(HelperUT):
    """Test cases for QEMUImg helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = QEMUImg()
        super(TestQEMUImg, self).setUp()

    def test_older_version(self):
        """Test .version getter logic for older versions."""
        self.fake_output = """
qemu-img version 1.4.2, Copyright (c) 2004-2008 Fabrice Bellard
usage: qemu-img command [command options]
QEMU disk image utility

Command syntax:
..."""
        version = self.helper.version
        self.assertEqual(self.last_argv[0], ['qemu-img', '--version'])
        self.assertEqual(version, StrictVersion("1.4.2"))

        # Output should be cached rather than re-invoking qemu-img
        self.last_argv = []
        self.fake_output = "Gotcha!"
        version = self.helper.version
        self.assertEqual(self.last_argv, [])
        self.assertEqual(version, StrictVersion("1.4.2"))

    def test_newer_version(self):
        """Test .version getter logic for newer versions."""
        self.fake_output = \
            "qemu-img version 2.1.2, Copyright (c) 2004-2008 Fabrice Bellard"
        self.assertEqual(self.helper.version,
                         StrictVersion("2.1.2"))

    def test_invalid_version(self):
        """Negative test for .version getter logic."""
        self.fake_output = "qemu-img: error: unknown argument --version"
        with self.assertRaises(RuntimeError):
            self.helper.version

    def test_install_helper_already_present(self):
        """Do nothing when trying to re-install."""
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_apt_get(self):
        """Test installation via 'apt-get'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = True
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['yum'] = False
        Helper._apt_updated = False
        self.fake_output = 'not installed'
        self.helper.install_helper()
        self.assertEqual([
            ['dpkg', '-s', 'qemu-utils'],
            ['sudo', 'apt-get', '-q', 'update'],
            ['sudo', 'apt-get', '-q', 'install', 'qemu-utils'],
        ], self.last_argv)
        self.assertTrue(Helper._apt_updated)
        # Make sure we don't call apt-get update again unnecessarily
        self.last_argv = []
        self.helper.install_helper()
        self.assertEqual([
            ['dpkg', '-s', 'qemu-utils'],
            ['sudo', 'apt-get', '-q', 'install', 'qemu-utils'],
        ], self.last_argv)

    def test_install_helper_port(self):
        """Test installation via 'port'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['port'] = True
        Helper.PACKAGE_MANAGERS['yum'] = False
        Helper._port_updated = False
        self.helper.install_helper()
        self.assertEqual([['sudo', 'port', 'selfupdate'],
                          ['sudo', 'port', 'install', 'qemu']],
                         self.last_argv)
        self.assertTrue(Helper._port_updated)
        # Make sure we don't call port selfupdate again unnecessarily
        self.last_argv = []
        self.helper.install_helper()
        self.assertEqual([['sudo', 'port', 'install', 'qemu']],
                         self.last_argv)

    def test_install_helper_yum(self):
        """Test installation via 'yum'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['yum'] = True
        self.helper.install_helper()
        self.assertEqual([['sudo', 'yum', '--quiet', 'install', 'qemu-img']],
                         self.last_argv)

    def test_install_helper_unsupported(self):
        """Installation fails without a package manager."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['yum'] = False
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

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

    def test_get_disk_format_not_available(self):
        """Negative test for get_disk_format() - bad command output."""
        # Haven't found a way yet to make qemu-img actually fail here
        # without returning a non-zero RC and triggering a HelperError,
        # so we'll have to fake it
        self.fake_output = "qemu-img info: unsupported command"
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

    def test_get_disk_capacity_not_available(self):
        """Negative test for get_disk_capacity() - bad command output."""
        # Haven't found a way yet to make qemu-img actually fail here
        # without returning a non-zero RC and triggering a HelperError,
        # so we'll have to fake it
        self.fake_output = "qemu-img info: unsupported command"
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
        with self.assertRaises(NotImplementedError):
            self.helper._version = StrictVersion("2.0.99")
            self.helper.convert_disk_image(self.blank_vmdk, self.temp_dir,
                                           'vmdk', 'streamOptimized')
