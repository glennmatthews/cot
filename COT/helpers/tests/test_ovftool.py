#!/usr/bin/env python
#
# test_ovftool.py - Unit test cases for COT.helpers.ovftool submodule.
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

"""Unit test cases for the COT.helpers.ovftool submodule."""

from .test_helper import HelperUT
from COT.helpers.helper import Helper
from COT.helpers.ovftool import OVFTool


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
