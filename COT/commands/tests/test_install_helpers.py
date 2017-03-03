#!/usr/bin/env python
# coding=utf-8
#
# install_helpers.py - test cases for the COTInstallHelpers class
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2015-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for COT.install_helpers.COTInstallHelpers class."""

import os
import sys

import mock

from COT.commands.tests.command_testcase import CommandTestCase
from COT.commands.install_helpers import COTInstallHelpers
from COT.helpers import HelperError, helpers
from COT.helpers.apt_get import AptGet
from COT.helpers.port import Port

# pylint: disable=missing-param-doc,missing-type-doc


def stub_check_output(arg_list, *_args, **_kwargs):
    """Stub to ensure fixed version number strings.

    Args:
      arg_list (list): arg_list[0] is script being called, others are ignored.

    Returns:
      str: Canned output line, or ""
    """
    versions = {
        "fatdisk": "fatdisk, version 1.0.0-beta",
        "genisoimage": "genisoimage 1.1.11 (Linux)",
        "mkisofs": "mkisofs 3.00 (--) Copyright (C) 1993-1997 "
        "Eric Youngdale (C) 1997-2010 Jörg Schilling",
        "ovftool": "VMware ovftool 4.0.0 (build-2301625)",
        "qemu-img": "qemu-img version 2.1.2, "
        "Copyright (c) 2004-2008 Fabrice Bellard",
        "vmdktool": "vmdktool version 1.4",
    }
    return versions.get(arg_list[0], "")


def stub_dir_exists_but_not_file(path):
    """Stub for :func:`os.path.exists`.

    Args:
      path (str): Path to check.
    Returns:
      bool: True for man dir, False for man file.
    """
    return os.path.basename(path) != "cot.1"


# pylint: disable=protected-access

class TestCOTInstallHelpers(CommandTestCase):
    """Test the COTInstallHelpers class."""

    command_class = COTInstallHelpers

    # pylint thinks self.command is a Command instead of a COTInstallHelpers,
    # so tell it to be quiet about members specific to COTInstallHelpers:
    # pylint: disable=no-member

    def setUp(self):
        """Do the appropriate setup before each test case."""
        super(TestCOTInstallHelpers, self).setUp()

        # Manpath location detected from argv0
        # /usr/local/bin/python --> /usr/local/man
        sys.argv[0] = "/foo/bar/bin/cot"
        self.manpath = os.path.join(
            os.path.dirname(os.path.dirname(sys.argv[0])), "man")

        # Fake out installation status
        for helper in helpers.values():
            helper._installed = None
            helper._path = None
            helper._version = None

    def tearDown(self):
        """Restore baseline behavior after each test case."""
        for helper in helpers.values():
            helper._installed = None
            helper._path = None
            helper._version = None
        super(TestCOTInstallHelpers, self).tearDown()

    @mock.patch('COT.helpers.helper.check_output',
                side_effect=stub_check_output)
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('filecmp.cmp', return_value=True)
    @mock.patch('distutils.spawn.find_executable')
    def test_verify_only(self, mock_find_executable, *_):
        """Make sure expected results are seen with --verify-only option."""
        def stub_find_executable(name):
            """Pretend to find every executable except ovftool."""
            if name == 'ovftool':
                return None
            return "/usr/local/bin/" + name

        mock_find_executable.side_effect = stub_find_executable

        self.command.verify_only = True
        expected_output = """
Results:
-------------
COT manpages: already installed, no updates needed
fatdisk:      version 1.0, present at /usr/local/bin/fatdisk
mkisofs:      version 3.0, present at /usr/local/bin/mkisofs
ovftool:      NOT FOUND
qemu-img:     version 2.1.2, present at /usr/local/bin/qemu-img
vmdktool:     version 1.4, present at /usr/local/bin/vmdktool
"""
        self.check_cot_output(expected_output)

    @mock.patch('COT.helpers.helper.check_output',
                side_effect=stub_check_output)
    @mock.patch('os.path.isdir', return_value=True)
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('filecmp.cmp', return_value=True)
    @mock.patch('COT.helpers.apt_get.AptGet.install_package')
    @mock.patch('COT.helpers.yum.Yum.install_package')
    @mock.patch('COT.helpers.port.Port.install_package')
    @mock.patch('distutils.spawn.find_executable')
    def test_install(self,
                     mock_find_executable,
                     mock_port_install,
                     mock_yum_install,
                     mock_apt_install,
                     *_):
        """Show results when pretending to install helpers."""
        paths = {
            "fatdisk": "/opt/local/bin/fatdisk",
        }

        for helper_name in helpers:
            helpers[helper_name]._installed = False

        helpers['fatdisk']._installed = True
        helpers['fatdisk']._path = "/opt/local/bin/fatdisk"

        def stub_find_executable(name):
            """Pretend to find every executable except ovftool."""
            return paths.get(name, None)

        def stub_install(package):
            """Fake successful or unsuccessful installation of tools."""
            if package == "genisoimage":
                helpers['genisoimage']._path = "/usr/bin/genisoimage"
                helpers['genisoimage']._installed = True
                return
            raise HelperError(1, "not really installing!")

        mock_find_executable.side_effect = stub_find_executable
        helpers['apt-get']._installed = True
        mock_apt_install.side_effect = stub_install
        helpers['port']._installed = True
        mock_port_install.side_effect = stub_install
        helpers['yum']._installed = True
        mock_yum_install.side_effect = stub_install
        AptGet._updated = False
        Port._updated = False
        expected_output = """
Results:
-------------
COT manpages: already installed, no updates needed
fatdisk:      version 1.0, present at /opt/local/bin/fatdisk
genisoimage:  successfully installed to /usr/bin/genisoimage, version 1.1.11
mkisofs:      INSTALLATION FAILED: [Errno 1] not really installing!
ovftool:      INSTALLATION FAILED: No support for automated installation of
              ovftool, as VMware requires a site login to download it. See
              https://www.vmware.com/support/developer/ovf/
qemu-img:     INSTALLATION FAILED: [Errno 1] not really installing!
vmdktool:     INSTALLATION FAILED: [Errno 1] not really installing!
"""
        # Normally we raise an error due to the failed installations
        with self.assertRaises(EnvironmentError):
            self.check_cot_output(expected_output)
        # ...but we can set ignore_errors to suppress this behavior
        self.command.ignore_errors = True
        # revert to initial state
        helpers["genisoimage"]._installed = False
        self.check_cot_output(expected_output)

    @mock.patch('os.path.exists', return_value=False)
    def test_manpages_helper_verify_dir_not_found(self, *_):
        """Call manpages_helper with verify-only, directory not found."""
        self.command.verify_only = True
        result, message = self.command.manpages_helper()
        self.assertTrue(result)  # verify-only returns True regardless
        self.assertEqual("DIRECTORY NOT FOUND: {0}/man1"
                         .format(self.manpath), message)

    @mock.patch('filecmp.cmp', return_value=True)
    @mock.patch('os.path.exists', side_effect=stub_dir_exists_but_not_file)
    def test_manpages_helper_verify_file_not_found(self, *_):
        """Call manpages_helper with verify-only, file not found."""
        self.command.verify_only = True
        result, message = self.command.manpages_helper()
        self.assertTrue(result)  # verify-only returns True regardless
        self.assertEqual("NOT FOUND", message)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('filecmp.cmp', return_value=False)
    def test_manpages_helper_verify_file_outdated(self, *_):
        """Call manpages_helper with verify-only, file not found."""
        self.command.verify_only = True
        result, message = self.command.manpages_helper()
        self.assertTrue(result)  # verify-only returns True regardless
        self.assertEqual("NEEDS UPDATE", message)

    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('COT.helpers.helper.check_call',
                side_effect=HelperError)
    @mock.patch('os.makedirs')
    def test_manpages_helper_create_dir_fail(self, mock_makedirs, *_):
        """Call manpages_helper with a simulated makedirs() failure."""
        mock_makedirs.side_effect = OSError(13, "Permission denied",
                                            os.path.join(self.manpath, 'man1'))

        result, message = self.command.manpages_helper()
        self.assertFalse(result)
        self.assertEqual("INSTALLATION FAILED: [Errno 13] "
                         "Permission denied: '{0}'"
                         .format(os.path.join(self.manpath, 'man1')),
                         message)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.path.isdir', return_value=True)
    @mock.patch('filecmp.cmp', return_value=False)
    @mock.patch('COT.helpers.helper.check_call',
                side_effect=HelperError)
    @mock.patch('shutil.copy')
    def test_manpages_helper_create_file_fail(self, mock_copy, *_):
        """Call manpages_helper with a simulated copy() failure."""
        mock_copy.side_effect = IOError(13, "Permission denied",
                                        "{0}/man1/cot.1".format(self.manpath))

        result, message = self.command.manpages_helper()
        self.assertFalse(result)
        self.assertEqual("INSTALLATION FAILED: [Errno 13] "
                         "Permission denied: '{0}/man1/cot.1'"
                         .format(self.manpath),
                         message)

    @mock.patch('shutil.copy')
    @mock.patch('filecmp.cmp', return_value=False)
    @mock.patch('os.makedirs', return_value=False)
    def test_manpages_helper_all_new(self, *_):
        """Call manpages_helper to simulate installing new manpages."""
        result, message = self.command.manpages_helper()
        self.assertTrue(result)
        self.assertEqual("successfully installed to {0}".format(self.manpath),
                         message)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.path.isdir', return_value=True)
    @mock.patch('shutil.copy')
    @mock.patch('filecmp.cmp', return_value=False)
    def test_manpages_helper_update(self, *_):
        """Call manpages_helper to simulate updating existing manpages."""
        result, message = self.command.manpages_helper()
        self.assertTrue(result)
        self.assertEqual("successfully updated in {0}".format(self.manpath),
                         message)
