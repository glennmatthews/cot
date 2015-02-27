#!/usr/bin/env python
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

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.install_helpers import COTInstallHelpers
from COT.helpers import FatDisk, MkIsoFS, OVFTool, QEMUImg, VmdkTool


class TestCOTInstallHelpers(COT_UT):

    """Test the COTInstallHelpers class."""

    def setUp(self):
        """Do the appropriate setup before each test case."""
        super(TestCOTInstallHelpers, self).setUp()
        self.instance = COTInstallHelpers(UI())

    def test_verify_only(self):
        """Make sure expected results are seen with --verify-only option."""
        self.instance.verify_only = True
        verify_result = {
            True: "already installed",
            False: "NOT installed"
        }
        expected_output = """
Results:
-------------
fatdisk:      {0}
mkisofs:      {1}
ovftool:      {2}
qemu-img:     {3}
vmdktool:     {4}
""".format(verify_result[(FatDisk().path is not None)],
           verify_result[(MkIsoFS().path is not None)],
           verify_result[(OVFTool().path is not None)],
           verify_result[(QEMUImg().path is not None)],
           verify_result[(VmdkTool().path is not None)])
        self.check_cot_output(expected_output)

    # def test_install(self):
