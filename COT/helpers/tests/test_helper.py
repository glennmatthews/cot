#!/usr/bin/env python
# coding=utf-8
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

"""Unit test cases for the COT.helpers package."""

import contextlib
import os
import logging
import sys

from distutils.version import StrictVersion

from COT.tests.ut import COT_UT
import COT.helpers.helper
from COT.helpers.helper import Helper
from COT.helpers import HelperError, HelperNotFoundError
from COT.helpers.fatdisk import FatDisk
from COT.helpers.mkisofs import MkIsoFS
from COT.helpers.ovftool import OVFTool
from COT.helpers.qemu_img import QEMUImg
from COT.helpers.vmdktool import VmdkTool

logger = logging.getLogger(__name__)


class HelperUT(COT_UT):

    """Generic class for testing Helper and subclasses thereof."""

    # commonly seen logger message for helpers
    ALREADY_INSTALLED = {
        'levelname': 'WARNING',
        'msg': "Tried to install .* but it's already available .*",
    }

    def stub_check_call(self, argv, require_success=True, **kwargs):
        """Stub for Helper._check_call - store the argv and do nothing."""
        logger.info("stub_check_call({0}, {1})"
                    .format(argv, require_success))
        self.last_argv.append(argv)

    def stub_check_output(self, argv, require_success=True, **kwargs):
        """Stub for Helper._check_output - return canned output."""
        logger.info("stub_check_output({0}, {1})"
                    .format(argv, require_success))
        self.last_argv.append(argv)
        if self.fake_output is not None:
            return self.fake_output
        return self._check_output(argv, require_success)

    def stub_find_executable(self, name):
        """Stub for Helper.find_executable - returns a fixed response."""
        logger.info("stub_find_executable({0})".format(name))
        return self.fake_path

    @contextlib.contextmanager
    def stub_download_and_expand(self, url):
        """Stub for Helper.download_and_expand - create a fake directory."""
        from COT.helpers.helper import TemporaryDirectory
        with TemporaryDirectory(prefix=("cot_ut_" + self.helper.name)) as d:
            yield d

    def stub_confirm(self, prompt, force=False):
        """Stub for confirm() - return fixed response."""
        return self.default_confirm_response

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        # subclass needs to set self.helper
        super(HelperUT, self).setUp()
        self.fake_output = None
        self.fake_path = None
        self.last_argv = []
        self._check_call = Helper._check_call
        Helper._check_call = self.stub_check_call
        self._check_output = Helper._check_output
        Helper._check_output = self.stub_check_output
        self._download_and_expand = Helper.download_and_expand
        Helper.download_and_expand = self.stub_download_and_expand
        self.default_confirm_response = True
        self._confirm = COT.helpers.helper.confirm
        COT.helpers.helper.confirm = self.stub_confirm
        # save some environment properties for sanity
        self._port = Helper.PACKAGE_MANAGERS['port']
        self._apt_get = Helper.PACKAGE_MANAGERS['apt-get']
        self._yum = Helper.PACKAGE_MANAGERS['yum']
        self._platform = sys.platform
        self._find_executable = Helper.find_executable

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        COT.helpers.helper.confirm = self._confirm
        Helper._check_call = self._check_call
        Helper._check_output = self._check_output
        Helper.download_and_expand = self._download_and_expand
        Helper.PACKAGE_MANAGERS['port'] = self._port
        Helper.PACKAGE_MANAGERS['apt-get'] = self._apt_get
        Helper.PACKAGE_MANAGERS['yum'] = self._yum
        sys.platform = self._platform
        Helper.find_executable = self._find_executable
        super(HelperUT, self).tearDown()


class HelperGenericTest(HelperUT):

    """Test cases for generic Helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = Helper("generic")
        super(HelperGenericTest, self).setUp()

    def test_check_call_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist."""
        Helper._check_call = self._check_call
        self.assertRaises(HelperNotFoundError,
                          Helper._check_call, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          Helper._check_call,
                          ["not_a_command"], require_success=True)

    def test_check_call_helpererror(self):
        """HelperError if executable fails and require_success is set."""
        Helper._check_call = self._check_call
        with self.assertRaises(HelperError) as cm:
            Helper._check_call(["false"])
        self.assertEqual(cm.exception.errno, 1)

        Helper._check_call(["false"], require_success=False)

    def test_check_output_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist."""
        self.assertRaises(HelperNotFoundError,
                          Helper._check_output, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          Helper._check_output, ["not_a_command"],
                          require_success=True)

    def test_check_output_helpererror(self):
        """HelperError if executable fails and require_success is set."""
        with self.assertRaises(HelperError) as cm:
            Helper._check_output(["false"])
        self.assertEqual(cm.exception.errno, 1)

        Helper._check_output(["false"], require_success=False)

    def test_helper_not_found(self):
        """Make sure helper.path is None if find_executable fails."""
        Helper.find_executable = self.stub_find_executable
        self.assertEqual(self.helper.path, None)

    def test_install_helper_already_present(self):
        """Make sure a warning is logged when attempting to re-install."""
        self.helper._path = True
        self.helper.install_helper()
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_call_helper_install(self):
        """call_helper will call install_helper, which raises an error."""
        self.assertRaises(NotImplementedError,
                          self.helper.call_helper, ["Hello!"])

    def test_call_helper_no_install(self):
        """If not installed, and user declines, raise HelperNotFoundError."""
        self.default_confirm_response = False
        self.assertRaises(HelperNotFoundError,
                          self.helper.call_helper, ["Hello!"])

    def test_download_and_expand(self):
        """Validate the download_and_expand() context_manager."""
        # Remove our stub for this test only
        Helper.download_and_expand = self._download_and_expand
        with Helper.download_and_expand(
            "http://github.com/glennmatthews/cot/archive/master.tar.gz"
        ) as directory:
            self.assertTrue(os.path.exists(directory))
            self.assertTrue(os.path.exists(
                os.path.join(directory, "cot-master")))
            self.assertTrue(os.path.exists(
                os.path.join(directory, "cot-master", "COT")))
            self.assertTrue(os.path.exists(
                os.path.join(directory, "cot-master", "COT", "tests")))
            self.assertTrue(os.path.exists(
                os.path.join(directory, "cot-master", "COT", "tests", "ut.py")
            ))
        # Temporary directory should be cleaned up when done
        self.assertFalse(os.path.exists(directory))


class TestFatDisk(HelperUT):

    """Test cases for FatDisk helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = FatDisk()
        super(TestFatDisk, self).setUp()

    def test_get_version(self):
        """Validate .version getter."""
        self.fake_output = "fatdisk, version 1.0.0-beta"
        self.assertEqual(StrictVersion("1.0.0"), self.helper.version)

    def test_install_helper_already_present(self):
        """Trying to re-install is a no-op."""
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_apt_get(self):
        """Test installation via 'apt-get'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['apt-get'] = True
        sys.platform = 'linux2'
        self.helper.install_helper()
        self.assertEqual([
            ['sudo', 'apt-get', '-q', 'install', 'make'],
            ['sudo', 'apt-get', '-q', 'install', 'gcc'],
            ['./RUNME'],
            ['sudo', 'cp', 'fatdisk', '/usr/local/bin/fatdisk'],
        ], self.last_argv)

    def test_install_helper_port(self):
        """Test installation via 'port'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['port'] = True
        self.helper.install_helper()
        self.assertEqual(self.last_argv[0],
                         ['sudo', 'port', 'install', 'fatdisk'])

    def test_install_helper_yum(self):
        """Test installation via 'yum'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['yum'] = True
        sys.platform = 'linux2'
        self.helper.install_helper()
        self.assertEqual([
            ['sudo', 'yum', '--quiet', 'install', 'make'],
            ['sudo', 'yum', '--quiet', 'install', 'gcc'],
            ['./RUNME'],
            ['sudo', 'cp', 'fatdisk', '/usr/local/bin/fatdisk'],
        ], self.last_argv)

    def test_install_helper_linux_need_make_no_package_manager(self):
        """Linux installation requires yum or apt-get if 'make' missing."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['yum'] = False
        sys.platform = 'linux2'
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

    def test_install_helper_linux_need_compiler_no_package_manager(self):
        """Linux installation requires yum or apt-get if 'gcc' missing."""
        def new_stub_find_executable(self, name):
            """Stub for Helper.find_executable - returns a fixed response."""
            logger.info("stub_find_executable({0})".format(name))
            if name == 'make':
                return "/bin/make"
            else:
                return None
        Helper.find_executable = new_stub_find_executable
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['yum'] = False
        sys.platform = 'linux2'
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

    def test_install_helper_unsupported(self):
        """No support for installation under Windows."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['port'] = False
        sys.platform = 'windows'
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()


class TestMkIsoFS(HelperUT):

    """Test cases for MkIsoFS helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = MkIsoFS()
        super(TestMkIsoFS, self).setUp()

    def test_get_version_mkisofs(self):
        """Test .version getter logic for mkisofs."""
        self.fake_output = ("mkisofs 3.00 (--) Copyright (C) 1993-1997 "
                            "Eric Youngdale (C) 1997-2010 Jörg Schilling")
        self.assertEqual(StrictVersion("3.0"), self.helper.version)

    def test_get_version_genisoimage(self):
        """Test .version getter logic for genisoimage."""
        self.fake_output = "genisoimage 1.1.11 (Linux)"
        self.assertEqual(StrictVersion("1.1.11"), self.helper.version)

    def test_find_mkisofs(self):
        """If mkisofs is found, use it."""
        def find_one(self, name):
            if name == "mkisofs":
                return "/mkisofs"
            return None
        Helper.find_executable = find_one
        self.assertEqual("mkisofs", self.helper.name)
        self.assertEqual(self.helper.path, "/mkisofs")

    def test_find_genisoimage(self):
        """If mkisofs is not found, but genisoimage is, use that."""
        def find_one(self, name):
            if name == "genisoimage":
                return "/genisoimage"
            return None
        Helper.find_executable = find_one
        self.assertEqual("genisoimage", self.helper.name)
        self.assertEqual(self.helper.path, "/genisoimage")

    def test_install_helper_already_present(self):
        """Don't re-install if already installed."""
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_port(self):
        """Test installation via 'port'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['port'] = True
        self.helper.install_helper()
        self.assertEqual([['sudo', 'port', 'install', 'cdrtools']],
                         self.last_argv)

    def test_install_helper_apt_get(self):
        """Test installation via 'apt-get'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = True
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['yum'] = False
        self.helper.install_helper()
        self.assertEqual([['sudo', 'apt-get', '-q', 'install', 'genisoimage']],
                         self.last_argv)
        self.assertEqual('genisoimage', self.helper.name)

    def test_install_helper_unsupported(self):
        """Installation fails with neither apt-get nor port nor yum."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['yum'] = False
        sys.platform = 'windows'
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()


class TestOVFTool(HelperUT):

    """Test cases for OVFTool helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = OVFTool()
        super(TestOVFTool, self).setUp()
        Helper.find_executable = self.stub_find_executable

    def test_invalid_version(self):
        """Negative test for .version getter logic."""
        self.fake_path = "/fake/ovftool"
        self.fake_output = "Error: Unknown option: 'version'"
        with self.assertRaises(RuntimeError):
            self.helper.version

    def test_install_helper_already_present(self):
        """Do nothing when trying to re-install."""
        self.fake_path = "/fake/ovftool"
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_unsupported(self):
        """No support for automated installation of ovftool."""
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

    def test_validate_ovf(self):
        """Try the validate_ovf() API."""
        self.fake_path = "/fake/ovftool"
        self.fake_output = ""
        self.helper.validate_ovf(self.input_ovf)
        self.assertEqual(['ovftool', '--schemaValidate', self.input_ovf],
                         self.last_argv[0])


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
        self.helper.install_helper()
        self.assertEqual([['sudo', 'apt-get', '-q', 'install', 'qemu-utils']],
                         self.last_argv)

    def test_install_helper_port(self):
        """Test installation via 'port'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['port'] = True
        Helper.PACKAGE_MANAGERS['yum'] = False
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


class TestVmdkTool(HelperUT):

    """Test cases for VmdkTool helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = VmdkTool()
        super(TestVmdkTool, self).setUp()

    def test_get_version(self):
        """Test .version getter logic."""
        self.fake_output = "vmdktool version 1.4"
        self.assertEqual(StrictVersion("1.4"), self.helper.version)

    def test_install_helper_already_present(self):
        """Do nothing instead of re-installing."""
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_apt_get(self):
        """Test installation via 'apt-get'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = True
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['yum'] = False
        sys.platform = 'linux2'
        self.helper.install_helper()
        self.assertEqual([
            ['sudo', 'apt-get', '-q', 'install', 'make'],
            ['sudo', 'apt-get', '-q', 'install', 'zlib1g-dev'],
            ['make', 'CFLAGS="-D_GNU_SOURCE -g -O -pipe"'],
            ['sudo', 'mkdir', '-p', '--mode=755', '/usr/local/man/man8'],
            ['sudo', 'make', 'install'],
        ], self.last_argv)

    def test_install_helper_port(self):
        """Test installation via 'port'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['port'] = True
        self.helper.install_helper()
        self.assertEqual(self.last_argv[0],
                         ['sudo', 'port', 'install', 'vmdktool'])

    def test_install_helper_yum(self):
        """Test installation via 'yum'."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['yum'] = True
        sys.platform = 'linux2'
        self.helper.install_helper()
        self.assertEqual([
            ['sudo', 'yum', '--quiet', 'install', 'make'],
            ['sudo', 'yum', '--quiet', 'install', 'zlib-devel'],
            ['make', 'CFLAGS="-D_GNU_SOURCE -g -O -pipe"'],
            ['sudo', 'mkdir', '-p', '--mode=755', '/usr/local/man/man8'],
            ['sudo', 'make', 'install'],
        ], self.last_argv)

    def test_install_helper_unsupported(self):
        """Unable to install without a package manager."""
        Helper.find_executable = self.stub_find_executable
        Helper.PACKAGE_MANAGERS['apt-get'] = False
        Helper.PACKAGE_MANAGERS['port'] = False
        Helper.PACKAGE_MANAGERS['yum'] = False
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

    def test_convert_unsupported(self):
        """Negative test - conversion to unsupported format/subformat."""
        with self.assertRaises(NotImplementedError):
            self.helper.convert_disk_image(self.blank_vmdk, self.temp_dir,
                                           'qcow2')
        with self.assertRaises(NotImplementedError):
            self.helper.convert_disk_image(self.blank_vmdk, self.temp_dir,
                                           'vmdk', 'monolithicSparse')
