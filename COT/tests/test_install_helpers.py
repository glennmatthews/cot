#!/usr/bin/env python
# coding=utf-8
#
# install_helpers.py - test cases for the COTInstallHelpers class
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2015-2016 the COT project developers.
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

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.install_helpers import COTInstallHelpers
from COT.helpers import HelperError
from COT.helpers.helper import Helper


def stub_check_output(arg_list, *_args, **_kwargs):
    """Stub to ensure fixed version number strings."""
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
    """Stub for os.path.exists; return true for man dir, false for man file."""
    return os.path.basename(path) != "cot.1"


class TestCOTInstallHelpers(COT_UT):
    """Test the COTInstallHelpers class."""

    def setUp(self):
        """Do the appropriate setup before each test case."""
        super(TestCOTInstallHelpers, self).setUp()
        self.instance = COTInstallHelpers(UI())

        # Manpath location detected from argv0
        # /usr/local/bin/python --> /usr/local/man
        sys.argv[0] = "/foo/bar/bin/cot"
        self.manpath = os.path.join(
            os.path.dirname(os.path.dirname(sys.argv[0])), "man")

    @mock.patch('COT.helpers.helper.Helper._check_output',
                side_effect=stub_check_output)
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('filecmp.cmp', return_value=True)
    @mock.patch('COT.helpers.helper.Helper.find_executable')
    def test_verify_only(self, mock_find_executable, *_):
        """Make sure expected results are seen with --verify-only option."""
        # pylint: disable=protected-access
        def stub_find_executable(name):
            """Pretend to find every executable except ovftool."""
            if name == 'ovftool':
                return None
            return "/usr/local/bin/" + name

        mock_find_executable.side_effect = stub_find_executable

        self.instance.verify_only = True
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

    @mock.patch('COT.helpers.helper.Helper._check_output',
                side_effect=stub_check_output)
    @mock.patch('os.path.isdir', return_value=True)
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('filecmp.cmp', return_value=True)
    @mock.patch('COT.helpers.helper.Helper.apt_install')
    @mock.patch('COT.helpers.helper.Helper.yum_install')
    @mock.patch('COT.helpers.helper.Helper.port_install')
    @mock.patch('COT.helpers.helper.Helper.find_executable')
    def test_install(self,
                     mock_find_executable,
                     mock_port_install,
                     mock_yum_install,
                     mock_apt_install,
                     *_):
        """Show results when pretending to install helpers."""
        # pylint: disable=protected-access
        paths = {
            "fatdisk": "/opt/local/bin/fatdisk",
            "mkisofs": None,
            "genisoimage": None,
            "ovftool": None,
            "qemu-img": None,
            "vmdktool": None
        }

        def stub_find_executable(name):
            """Get canned paths for various executables."""
            return paths.get(name, None)

        def stub_install(package):
            """Fake successful or unsuccessful installation of tools."""
            if package == "genisoimage":
                paths["genisoimage"] = "/usr/bin/genisoimage"
                return True
            elif package == "cdrtools":
                return False
            raise HelperError(1, "not really installing!")

        mock_find_executable.side_effect = stub_find_executable
        mock_apt_install.side_effect = stub_install
        mock_port_install.side_effect = stub_install
        mock_yum_install.side_effect = stub_install
        Helper._apt_updated = False
        Helper._port_updated = False
        expected_output = """
Results:
-------------
COT manpages: already installed, no updates needed
fatdisk:      version 1.0, present at /opt/local/bin/fatdisk
genisoimage:  successfully installed to /usr/bin/genisoimage, version 1.1.11
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
        self.instance.ignore_errors = True
        # revert to initial state
        paths["genisoimage"] = None
        self.check_cot_output(expected_output)

    @mock.patch('os.path.exists', return_value=False)
    def test_manpages_helper_verify_dir_not_found(self, *_):
        """Call manpages_helper with verify-only, directory not found."""
        self.instance.verify_only = True
        result, message = self.instance.manpages_helper()
        self.assertTrue(result)  # verify-only returns True regardless
        self.assertEqual("DIRECTORY NOT FOUND: {0}/man1"
                         .format(self.manpath), message)

    @mock.patch('filecmp.cmp', return_value=True)
    @mock.patch('os.path.exists', side_effect=stub_dir_exists_but_not_file)
    def test_manpages_helper_verify_file_not_found(self, *_):
        """Call manpages_helper with verify-only, file not found."""
        self.instance.verify_only = True
        result, message = self.instance.manpages_helper()
        self.assertTrue(result)  # verify-only returns True regardless
        self.assertEqual("NOT FOUND", message)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('filecmp.cmp', return_value=False)
    def test_manpages_helper_verify_file_outdated(self, *_):
        """Call manpages_helper with verify-only, file not found."""
        self.instance.verify_only = True
        result, message = self.instance.manpages_helper()
        self.assertTrue(result)  # verify-only returns True regardless
        self.assertEqual("NEEDS UPDATE", message)

    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('COT.helpers.helper.Helper._check_call',
                side_effect=HelperError)
    @mock.patch('os.makedirs')
    def test_manpages_helper_create_dir_fail(self, mock_makedirs, *_):
        """Call manpages_helper with a simulated makedirs() failure."""
        mock_makedirs.side_effect = OSError(13, "Permission denied",
                                            os.path.join(self.manpath, 'man1'))

        result, message = self.instance.manpages_helper()
        self.assertFalse(result)
        self.assertEqual("INSTALLATION FAILED: [Errno 13] "
                         "Permission denied: '{0}'"
                         .format(os.path.join(self.manpath, 'man1')),
                         message)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.path.isdir', return_value=True)
    @mock.patch('filecmp.cmp', return_value=False)
    @mock.patch('COT.helpers.helper.Helper._check_call',
                side_effect=HelperError)
    @mock.patch('shutil.copy')
    def test_manpages_helper_create_file_fail(self, mock_copy, *_):
        """Call manpages_helper with a simulated copy() failure."""
        mock_copy.side_effect = IOError(13, "Permission denied",
                                        "{0}/man1/cot.1".format(self.manpath))

        result, message = self.instance.manpages_helper()
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
        result, message = self.instance.manpages_helper()
        self.assertTrue(result)
        self.assertEqual("successfully installed to {0}".format(self.manpath),
                         message)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.path.isdir', return_value=True)
    @mock.patch('shutil.copy')
    @mock.patch('filecmp.cmp', return_value=False)
    def test_manpages_helper_update(self, *_):
        """Call manpages_helper to simulate updating existing manpages."""
        result, message = self.instance.manpages_helper()
        self.assertTrue(result)
        self.assertEqual("successfully updated in {0}".format(self.manpath),
                         message)
