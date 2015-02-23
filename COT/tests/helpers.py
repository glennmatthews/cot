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
import sys

from distutils.version import StrictVersion

from COT.tests.ut import COT_UT
from COT.helpers import Helper, HelperError, HelperNotFoundError
from COT.helpers import FatDisk, MkIsoFS, OVFTool, QEMUImg, VmdkTool
import COT.ui_shared

logger = logging.getLogger(__name__)


class HelpersUT(COT_UT):
    """Generic class for testing Helpers and subclasses thereof."""

    # commonly seen logger message for helpers
    ALREADY_INSTALLED = {
        'levelname': 'WARNING',
        'msg': "Tried to install .* but it's already available .*",
    }

    def stub_check_call(self, argv, require_success=True, **kwargs):
        logger.info("stub_check_call({0}, {1})"
                    .format(argv, require_success))
        self.last_argv.append(argv)

    def stub_check_output(self, argv, require_success=True, **kwargs):
        logger.info("stub_check_output({0}, {1})"
                    .format(argv, require_success))
        self.last_argv.append(argv)
        if self.fake_output:
            return self.fake_output
        return self._check_output(argv, require_success)

    def stub_find_helper(self):
        logger.info("stub_find_helper()")
        return False

    def stub_find_executable(self, name):
        logger.info("stub_find_executable({0})".format(name))
        return None

    def setUp(self):
        # subclass needs to set self.helper
        super(HelpersUT, self).setUp()
        self.fake_output = None
        self.last_argv = []
        self._check_call = self.helper._check_call
        self.helper._check_call = self.stub_check_call
        self._check_output = self.helper._check_output
        self.helper._check_output = self.stub_check_output
        # save some environment properties for sanity
        self._port = self.helper.PACKAGE_MANAGERS['port']
        self._apt_get = self.helper.PACKAGE_MANAGERS['apt-get']
        self._yum = self.helper.PACKAGE_MANAGERS['yum']
        self._platform = sys.platform

    def tearDown(self):
        self.helper._check_call = self._check_call
        self.helper._check_output = self._check_output
        self.helper.PACKAGE_MANAGERS['port'] = self._port
        self.helper.PACKAGE_MANAGERS['apt-get'] = self._apt_get
        self.helper.PACKAGE_MANAGERS['yum'] = self._yum
        sys.platform = self._platform
        super(HelpersUT, self).tearDown()


class HelperGenericTest(HelpersUT):
    """Test cases for generic Helpers class."""

    def setUp(self):
        self.helper = Helper("generic")
        super(HelperGenericTest, self).setUp()

    def test_check_call_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist"""
        self.helper._check_call = self._check_call
        self.assertRaises(HelperNotFoundError,
                          self.helper._check_call, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          self.helper._check_call,
                          ["not_a_command"], require_success=True)

    def test_check_call_helpererror(self):
        """HelperError if executable fails and require_success is set"""
        self.helper._check_call = self._check_call
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

    def test_find_helper_not_found(self):
        self.helper.find_executable = self.stub_find_executable
        self.assertFalse(self.helper.find_helper())

    def test_version_abstract(self):
        self.helper.helper_path = True
        with self.assertRaises(NotImplementedError):
            self.helper.version

    def test_install_helper_already_present(self):
        self.helper.helper_path = True
        self.helper.install_helper()
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_call_helper_install(self):
        self.assertRaises(NotImplementedError,
                          self.helper.call_helper, ["Hello!"])

    def test_call_helper_no_install(self):
        COT.ui_shared.CURRENT_UI.default_confirm_response = False
        try:
            self.assertRaises(HelperNotFoundError,
                              self.helper.call_helper, ["Hello!"])
        finally:
            COT.ui_shared.CURRENT_UI.default_confirm_response = True


class TestFatDisk(HelpersUT):
    """Test cases for FatDisk helper class."""

    def setUp(self):
        self.helper = FatDisk()
        super(TestFatDisk, self).setUp()

    def test_get_version(self):
        self.fake_output = "fatdisk, version 1.0.0-beta"
        self.assertEqual(StrictVersion("1.0.0"), self.helper.version)

    def test_install_helper_already_present(self):
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_apt_get_no_make(self):
        self.helper.find_executable = self.stub_find_executable
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['port'] = False
        self.helper.PACKAGE_MANAGERS['apt-get'] = True
        sys.platform = 'linux2'
        self.helper.install_helper()
        self.assertEqual([
            ['sudo', 'apt-get', 'install', 'make'],
            ['sudo', 'apt-get', 'install', 'gcc'],
            ['wget', '-O', 'fatdisk.tgz', 'https://github.com/goblinhack/'
             'fatdisk/archive/v1.0.0-beta.tar.gz'],
            ['tar', 'zxf', 'fatdisk.tgz'],
            ['./RUNME'],
            ['sudo', 'cp', 'fatdisk-1.0.0-beta/fatdisk',
             '/usr/local/bin/fatdisk'],
        ], self.last_argv)

    def test_install_helper_port(self):
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['port'] = True
        self.helper.install_helper()
        self.assertEqual(self.last_argv[0],
                         ['sudo', 'port', 'install', 'fatdisk'])

    def test_install_helper_yum_no_make(self):
        self.helper.find_executable = self.stub_find_executable
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['port'] = False
        self.helper.PACKAGE_MANAGERS['apt-get'] = False
        self.helper.PACKAGE_MANAGERS['yum'] = True
        sys.platform = 'linux2'
        # we don't support installing 'make' from yum yet
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

    def test_install_helper_unsupported(self):
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['port'] = False
        sys.platform = 'windows'
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()


class TestMkIsoFS(HelpersUT):
    """Test cases for MkIsoFS helper class."""

    def setUp(self):
        self.helper = MkIsoFS()
        super(TestMkIsoFS, self).setUp()

    def test_get_version(self):
        # TODO - this output should have an umlaut...
        self.fake_output = ("mkisofs 3.00 (--) Copyright (C) 1993-1997 "
                            "Eric Youngdale (C) 1997-2010 J?rg Schilling")
        self.assertEqual(StrictVersion("3.0"), self.helper.version)

    def test_find_helper_failover(self):
        self.helper.find_executable = self.stub_find_executable
        self.assertEqual("mkisofs", self.helper.helper)
        self.assertFalse(self.helper.find_helper())
        self.assertEqual("genisoimage", self.helper.helper)
        self.assertFalse(self.helper.find_helper())

    def test_install_helper_already_present(self):
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_port(self):
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['apt-get'] = False
        self.helper.PACKAGE_MANAGERS['port'] = True
        self.helper.install_helper()
        self.assertEqual([['sudo', 'port', 'install', 'cdrtools']],
                         self.last_argv)

    def test_install_helper_apt_get(self):
        self.helper.find_executable = self.stub_find_executable
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['port'] = False
        self.helper.PACKAGE_MANAGERS['apt-get'] = True
        self.helper.install_helper()
        self.assertEqual([['sudo', 'apt-get', 'install', 'genisoimage']],
                         self.last_argv)
        self.assertEqual('genisoimage', self.helper.helper)

    def test_install_helper_unsupported(self):
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['port'] = False
        sys.platform = 'windows'
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()


class TestOVFTool(HelpersUT):
    """Test cases for OVFTool helper class."""

    def setUp(self):
        self.helper = OVFTool()
        super(TestOVFTool, self).setUp()

    def test_invalid_version(self):
        self.fake_output = "Error: Unknown option: 'version'"
        with self.assertRaises(AttributeError):
            self.helper.version

    def test_install_helper_already_present(self):
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_unsupported(self):
        self.helper.find_helper = self.stub_find_helper
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()


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
        self.assertEqual(self.last_argv[0], ['qemu-img', '--version'])
        self.assertEqual(version, StrictVersion("1.4.2"))

        # Output should be cached rather than re-invoking qemu-img
        self.last_argv = []
        self.fake_output = "Gotcha!"
        version = self.helper.version
        self.assertEqual(self.last_argv, [])
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

    def test_install_helper_already_present(self):
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_apt_get(self):
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['apt-get'] = True
        self.helper.PACKAGE_MANAGERS['port'] = False
        self.helper.PACKAGE_MANAGERS['yum'] = False
        self.helper.install_helper()
        self.assertEqual([['sudo', 'apt-get', 'install', 'qemu-utils']],
                         self.last_argv)

    def test_install_helper_port(self):
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['apt-get'] = False
        self.helper.PACKAGE_MANAGERS['port'] = True
        self.helper.PACKAGE_MANAGERS['yum'] = False
        self.helper.install_helper()
        self.assertEqual([['sudo', 'port', 'install', 'qemu']],
                         self.last_argv)

    def test_install_helper_yum(self):
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['apt-get'] = False
        self.helper.PACKAGE_MANAGERS['port'] = False
        self.helper.PACKAGE_MANAGERS['yum'] = True
        self.helper.install_helper()
        self.assertEqual([['sudo', 'yum', 'install', 'qemu-img']],
                         self.last_argv)

    def test_install_helper_unsupported(self):
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['apt-get'] = False
        self.helper.PACKAGE_MANAGERS['port'] = False
        self.helper.PACKAGE_MANAGERS['yum'] = False
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

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

    def test_create_invalid(self):
        """Invalid arguments."""
        # If extension not given, cannot guess file format
        self.assertRaises(RuntimeError,
                          self.helper.create_blank_disk,
                          os.path.join(self.temp_dir, "out"),
                          capacity="1M")

    def test_convert_unsupported(self):
        with self.assertRaises(NotImplementedError):
            self.helper.convert_disk_image(
                os.path.join(os.path.dirname(__file__), "blank.vmdk"),
                self.temp_dir, 'vhd')
        with self.assertRaises(NotImplementedError):
            self.helper._version = StrictVersion("2.0.99")
            self.helper.convert_disk_image(
                os.path.join(os.path.dirname(__file__), "blank.vmdk"),
                self.temp_dir, 'vmdk', 'streamOptimized')


class TestVmdkTool(HelpersUT):
    """Test cases for VmdkTool helper class."""

    def setUp(self):
        self.helper = VmdkTool()
        super(TestVmdkTool, self).setUp()

    def test_get_version(self):
        self.fake_output = "vmdktool version 1.4"
        self.assertEqual(StrictVersion("1.4"), self.helper.version)

    def test_install_helper_already_present(self):
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_apt_get_no_make(self):
        self.helper.find_executable = self.stub_find_executable
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['apt-get'] = True
        self.helper.PACKAGE_MANAGERS['port'] = False
        self.helper.install_helper()
        self.assertEqual([
            ['sudo', 'apt-get', 'install', 'make'],
            ['sudo', 'apt-get', 'install', 'zlib1g-dev'],
            ['wget', 'http://people.freebsd.org/~brian/'
             'vmdktool/vmdktool-1.4.tar.gz'],
            ['tar', 'zxf', 'vmdktool-1.4.tar.gz'],
            ['make', 'CFLAGS=-D_GNU_SOURCE -g -O -pipe',
             '--directory', 'vmdktool-1.4'],
            ['sudo', 'mkdir', '-p', '--mode=755', '/usr/local/man/man8'],
            ['sudo', 'make', '--directory', 'vmdktool-1.4', 'install'],
        ], self.last_argv)

    def test_install_helper_port(self):
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['port'] = True
        self.helper.install_helper()
        self.assertEqual(self.last_argv[0],
                         ['sudo', 'port', 'install', 'vmdktool'])

    def test_install_helper_yum_no_make(self):
        self.helper.find_executable = self.stub_find_executable
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['apt-get'] = False
        self.helper.PACKAGE_MANAGERS['port'] = False
        self.helper.PACKAGE_MANAGERS['yum'] = True
        self.helper.install_helper()
        self.assertEqual([
            ['sudo', 'yum', 'install', 'make'],
            ['sudo', 'yum', 'install', 'zlib-devel'],
            ['wget', 'http://people.freebsd.org/~brian/'
             'vmdktool/vmdktool-1.4.tar.gz'],
            ['tar', 'zxf', 'vmdktool-1.4.tar.gz'],
            ['make', 'CFLAGS=-D_GNU_SOURCE -g -O -pipe',
             '--directory', 'vmdktool-1.4'],
            ['sudo', 'mkdir', '-p', '--mode=755', '/usr/local/man/man8'],
            ['sudo', 'make', '--directory', 'vmdktool-1.4', 'install'],
        ], self.last_argv)

    def test_install_helper_unsupported(self):
        self.helper.find_helper = self.stub_find_helper
        self.helper.PACKAGE_MANAGERS['apt-get'] = False
        self.helper.PACKAGE_MANAGERS['port'] = False
        self.helper.PACKAGE_MANAGERS['yum'] = False
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

    def test_convert_unsupported(self):
        with self.assertRaises(NotImplementedError):
            self.helper.convert_disk_image(
                os.path.join(os.path.dirname(__file__), "blank.vmdk"),
                self.temp_dir, 'qcow2')
        with self.assertRaises(NotImplementedError):
            self.helper.convert_disk_image(
                os.path.join(os.path.dirname(__file__), "blank.vmdk"),
                self.temp_dir, 'vmdk', 'monolithicSparse')
