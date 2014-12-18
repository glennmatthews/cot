#!/usr/bin/env python
#
# inject_config.py - test cases for the COTInjectConfig class
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

import os.path

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.inject_config import COTInjectConfig
from COT.data_validation import InvalidInputError
from COT.platform import *

class TestCOTInjectConfig(COT_UT):

    def setUp(self):
        """Test case setup function called automatically prior to each test"""
        super(TestCOTInjectConfig, self).setUp()
        self.instance = COTInjectConfig(UI())
        self.instance.set_value("PACKAGE", self.input_ovf)

    def test_not_ready_with_no_args(self):
        ready, reason = self.instance.ready_to_run()
        self.assertEqual(ready, False)
        self.assertRegexpMatches(reason, "No configuration files")
        self.assertRaises(InvalidInputError, self.instance.run)

    def test_invalid_always_args(self):
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "config_file", 0)
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "secondary_config_file", 0)

    def test_valid_by_platform(self):
        config_file = os.path.join(os.path.dirname(__file__),
                                   "sample_cfg.txt")
        # IOSXRvLC supports neither primary nor secondary config files
        self.instance.vm.platform = IOSXRvLC
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "config_file", config_file)
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "secondary_config_file",
                          config_file)
        # IOSv supports primary but not secondary
        self.instance.vm.platform = IOSv
        self.instance.set_value("config_file", config_file)
        self.assertRaises(InvalidInputError,
                          self.instance.set_value, "secondary_config_file",
                          config_file)
        # IOSXRv supports both
        self.instance.vm.platform = IOSXRv
        self.instance.set_value("config_file", config_file)
        self.instance.set_value("secondary_config_file", config_file)
