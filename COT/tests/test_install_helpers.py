#!/usr/bin/env python
# coding=utf-8
#
# install_helpers.py - test cases for the COTInstallHelpers class
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2015 the COT project developers.
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

import filecmp
import os
import shutil
import sys

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.install_helpers import COTInstallHelpers
from COT.helpers import HelperError
from COT.helpers.helper import Helper


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
        # Hash of directories to override os.path.exists for.
        # If an explicit match is found for a file, returns that value.
        # Otherwise, walk back up the directory tree and see if there's a
        # match for a parent directory. If that doesn't match either, call
        # the real os.path.exists
        self.exists = {
            os.path.join(self.manpath, 'man1'): True,
        }
        # As above but for filecmp.cmp
        self.cmp = {
            os.path.join(self.manpath, 'man1'): True,
        }
        self._os_path_exists = os.path.exists
        os.path.exists = self.stub_exists
        self._cmp = filecmp.cmp
        filecmp.cmp = self.stub_cmp

    def cleanUp(self):
        """Cleanup after each test case."""
        os.path.exists = self._os_path_exists
        filecmp.cmp = self._cmp

    def stub_check_output(self, args, require_success=True, **kwargs):
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
        return versions.get(args[0], "")

    def stub_exists(self, path):
        """Stub for os.path.exists."""
        dir_path = path
        while dir_path and dir_path != "/":
            if dir_path in self.exists.keys():
                return self.exists[dir_path]
            dir_path = os.path.dirname(dir_path)
        return self._os_path_exists(path)

    def stub_cmp(self, f1, f2):
        """Stub for filecmp.cmp."""
        for path in [f1, f2]:
            while path and path != "/":
                if path in self.cmp.keys():
                    return self.cmp[path]
                path = os.path.dirname(path)
        return self._cmp(f1, f2)

    def test_verify_only(self):
        """Make sure expected results are seen with --verify-only option."""
        def stub_find_executable(self, name):
            if name == 'ovftool':
                return None
            return "/usr/local/bin/" + name

        _find_executable = Helper.find_executable
        Helper.find_executable = stub_find_executable
        _check_output = Helper._check_output
        Helper._check_output = self.stub_check_output

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
        try:
            self.check_cot_output(expected_output)
        finally:
            Helper.find_executable = _find_executable
            Helper._check_output = _check_output

    def test_install(self):
        """Show results when pretending to install helpers."""
        paths = {
            "fatdisk": "/opt/local/bin/fatdisk",
            "mkisofs": None,
            "genisoimage": None,
            "ovftool": None,
            "qemu-img": None,
            "vmdktool": None
        }

        def stub_find_executable(self, name):
            return paths.get(name, None)

        def stub_install(cls, package):
            if package == "genisoimage":
                paths["genisoimage"] = "/usr/bin/genisoimage"
                return True
            elif package == "cdrtools":
                return False
            raise HelperError(1, "not really installing!")

        _find_executable = Helper.find_executable
        _apt_install = Helper.apt_install
        _port_install = Helper.port_install
        _yum_install = Helper.yum_install
        _check_output = Helper._check_output
        Helper._check_output = self.stub_check_output
        Helper.find_executable = stub_find_executable
        Helper.apt_install = classmethod(stub_install)
        Helper.port_install = classmethod(stub_install)
        Helper.yum_install = classmethod(stub_install)
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
        try:
            # Normally we raise an error due to the failed installations
            with self.assertRaises(EnvironmentError):
                self.check_cot_output(expected_output)
            # ...but we can set ignore_errors to suppress this behavior
            self.instance.ignore_errors = True
            # revert to initial state
            paths["genisoimage"] = None
            self.check_cot_output(expected_output)
        finally:
            Helper.find_executable = _find_executable
            Helper.apt_install = _apt_install
            Helper.port_install = _port_install
            Helper.yum_install = _yum_install
            Helper._check_output = _check_output

    def test_install_manpages_verify_dir_not_found(self):
        """Call install_manpages with verify-only, directory not found."""
        self.exists[os.path.join(self.manpath, 'man1')] = False
        self.instance.verify_only = True
        result, message = self.instance.install_manpages()
        self.assertTrue(result)  # verify-only returns True regardless
        self.assertEqual("DIRECTORY NOT FOUND: {0}/man1"
                         .format(self.manpath), message)

    def test_install_manpages_verify_file_not_found(self):
        """Call install_manpages with verify-only, file not found."""
        self.exists[os.path.join(self.manpath, 'man1', 'cot.1')] = False
        self.instance.verify_only = True
        result, message = self.instance.install_manpages()
        self.assertTrue(result)  # verify-only returns True regardless
        self.assertEqual("NOT FOUND", message)

    def test_install_manpages_verify_file_outdated(self):
        """Call install_manpages with verify-only, file not found."""
        self.cmp[os.path.join(self.manpath, 'man1', 'cot.1')] = False
        self.instance.verify_only = True
        result, message = self.instance.install_manpages()
        self.assertTrue(result)  # verify-only returns True regardless
        self.assertEqual("NEEDS UPDATE", message)

    def test_install_manpages_create_dir_fail(self):
        """Call install_manpages with a simulated makedirs() failure."""
        self.exists[os.path.join(self.manpath, 'man1')] = False

        def makedirs(*args, **kwargs):
            raise OSError(13, "Permission denied",
                          os.path.join(self.manpath, 'man1'))
        _makedirs = os.makedirs
        os.makedirs = makedirs
        try:
            result, message = self.instance.install_manpages()
            self.assertFalse(result)
            self.assertEqual("INSTALLATION FAILED: [Errno 13] "
                             "Permission denied: '{0}'"
                             .format(os.path.join(self.manpath, 'man1')),
                             message)
        finally:
            os.makedirs = _makedirs

    def test_install_manpages_create_file_fail(self):
        """Call install_manpages with a simulated copy() failure."""
        self.cmp[os.path.join(self.manpath, 'man1', 'cot.1')] = False

        def copy(*args, **kwargs):
            raise IOError(13, "Permission denied",
                          "{0}/man1/cot.1".format(self.manpath))
        _shutil_copy = shutil.copy
        shutil.copy = copy

        try:
            result, message = self.instance.install_manpages()
            self.assertFalse(result)
            self.assertEqual("INSTALLATION FAILED: [Errno 13] "
                             "Permission denied: '{0}/man1/cot.1'"
                             .format(self.manpath),
                             message)
        finally:
            shutil.copy = _shutil_copy

    def test_install_manpages_all_new(self):
        """Call install_manpages to simulate installing new manpages."""
        self.exists[os.path.join(self.manpath, 'man1')] = False
        self.cmp[os.path.join(self.manpath, 'man1')] = False

        def makedirs(*args, **kwargs):
            pass
        _makedirs = os.makedirs
        os.makedirs = makedirs

        def copy(*args, **kwargs):
            pass
        _shutil_copy = shutil.copy
        shutil.copy = copy

        try:
            result, message = self.instance.install_manpages()
            self.assertTrue(result)
            self.assertEqual("successfully installed to {0}"
                             .format(self.manpath),
                             message)
        finally:
            os.makedirs = _makedirs
            shutil.copy = _shutil_copy

    def test_install_manpages_update(self):
        """Call install_manpages to simulate updating existing manpages."""
        self.cmp[os.path.join(self.manpath, 'man1', 'cot.1')] = False

        def copy(*args, **kwargs):
            pass
        _shutil_copy = shutil.copy
        shutil.copy = copy

        try:
            result, message = self.instance.install_manpages()
            self.assertTrue(result)
            self.assertEqual("successfully updated in {0}"
                             .format(self.manpath),
                             message)
        finally:
            shutil.copy = _shutil_copy
