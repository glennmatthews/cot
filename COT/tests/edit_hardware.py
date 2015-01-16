#!/usr/bin/env python
#
# edit_hardware.py - test cases for the COTEditHardware class
#
# December 2014, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

import re

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.edit_hardware import COTEditHardware
from COT.data_validation import InvalidInputError
from COT.platform import *

class TestCOTEditHardware(COT_UT):

    def setUp(self):
        """Test case setup function called automatically prior to each test"""
        super(TestCOTEditHardware, self).setUp()
        self.instance = COTEditHardware(UI())
        self.instance.set_value("PACKAGE", self.input_ovf)

    def test_not_ready_with_no_args(self):
        ready, reason = self.instance.ready_to_run()
        self.assertEqual(ready, False)
        self.assertTrue(re.search("No work requested", reason))
        self.assertRaises(InvalidInputError, self.instance.run)

    def test_valid_args(self):
        self.instance.set_value("cpus", "1")
        self.assertEqual(self.instance.get_value("cpus"), 1)
        self.instance.set_value("memory", "1GB")
        self.assertEqual(self.instance.get_value("memory"), 1024)
        self.instance.set_value("memory", "2g")
        self.assertEqual(self.instance.get_value("memory"), 2048)
        self.instance.set_value("memory", "256M")
        self.assertEqual(self.instance.get_value("memory"), 256)
        self.instance.set_value("memory", "1024")
        self.assertEqual(self.instance.get_value("memory"), 1024)
        self.instance.set_value("nics", 1)
        self.assertEqual(self.instance.get_value("nics"), 1)
        self.instance.set_value("serial_ports", 1)
        self.assertEqual(self.instance.get_value("serial_ports"), 1)

    def test_invalid_always_args(self):
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "cpus", 0)
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "cpus", "a")
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "memory", 0)
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "memory", "GB")
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "nics", -1)
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "nics", "b")
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "serial_ports", -1)
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "serial_ports", "c")


    def test_valid_by_platform(self):
        # IOSv only supports 1 vCPU and up to 3 GB of RAM
        self.instance.vm.platform = IOSv
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "cpus", 2)
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "memory", "4GB")
        #...but IOSXRv supports up to 8 CPUs and 3-8 GB of RAM
        self.instance.vm.platform = IOSXRv
        self.instance.set_value("cpus", 2)
        self.instance.set_value("cpus", 8)
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "cpus", 9)
        self.instance.set_value("memory", "4GB")
        self.instance.set_value("memory", "8GB")
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "memory", "9GB")
