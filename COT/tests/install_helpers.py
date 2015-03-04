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

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.install_helpers import COTInstallHelpers
from COT.helpers import Helper, HelperError


class TestCOTInstallHelpers(COT_UT):

    """Test the COTInstallHelpers class."""

    def setUp(self):
        """Do the appropriate setup before each test case."""
        super(TestCOTInstallHelpers, self).setUp()
        self.instance = COTInstallHelpers(UI())

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

        def stub_install(self, package):
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
        Helper.apt_install = stub_install
        Helper.port_install = stub_install
        Helper.yum_install = stub_install
        expected_output = """
Results:
-------------
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
