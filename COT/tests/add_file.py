#!/usr/bin/env python
#
# add_file.py - test cases for the COTAddFile class
#
# January 2015, Glenn F. Matthews
# Copyright (c) 2013-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

import os.path

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.add_file import COTAddFile
from COT.data_validation import InvalidInputError


class TestCOTAddFile(COT_UT):
    """Test cases for the COTAddFile module"""
    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCOTAddFile, self).setUp()
        self.instance = COTAddFile(UI())
        self.instance.set_value("output", self.temp_file)

    def test_readiness(self):
        """Test ready_to_run() under various combinations of parameters."""
        ready, reason = self.instance.ready_to_run()
        self.assertFalse(ready)
        self.assertEqual("FILE is a mandatory argument!", reason)
        self.assertRaises(InvalidInputError, self.instance.run)

        self.instance.set_value("FILE", self.iosv_ovf)
        ready, reason = self.instance.ready_to_run()
        self.assertFalse(ready)
        self.assertEqual("PACKAGE is a mandatory argument!", reason)
        self.assertRaises(InvalidInputError, self.instance.run)

        self.instance.set_value("PACKAGE", self.input_ovf)
        ready, reason = self.instance.ready_to_run()
        self.assertTrue(ready)

    def test_add_file(self):
        """Basic file addition"""
        self.instance.set_value("PACKAGE", self.input_ovf)
        self.instance.set_value("FILE", self.iosv_ovf)
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="iosv.ovf" ovf:id="iosv.ovf" ovf:size="{ovf_size}" />
   </ovf:References>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           ovf_size=os.path.getsize(self.iosv_ovf)))

    def test_add_file_with_id(self):
        """Add a file with explicit 'file_id' argument."""
        self.instance.set_value("PACKAGE", self.input_ovf)
        self.instance.set_value("FILE", self.iosv_ovf)
        self.instance.set_value("file_id", "myfile")
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="iosv.ovf" ovf:id="myfile" ovf:size="{ovf_size}" />
   </ovf:References>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           ovf_size=os.path.getsize(self.iosv_ovf)))
