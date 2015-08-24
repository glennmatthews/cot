#!/usr/bin/env python
#
# deploy.py - test cases for the COTDeploy class and helpers
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

"""Unit test cases for the COT.deploy.COTDeploy class and helpers."""

import logging
import re

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.deploy import COTDeploy
from COT.data_validation import InvalidInputError

logger = logging.getLogger(__name__)


class TestCOTDeploy(COT_UT):

    """Test cases for COTDeploy."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCOTDeploy, self).setUp()
        self.instance = COTDeploy(UI())
        self.instance.package = self.input_ovf

    def test_not_ready_with_no_args(self):
        """Verify that ready_to_run() is False without all mandatory args."""
        ready, reason = self.instance.ready_to_run()
        self.assertEqual(ready, False)
        self.assertTrue(re.search("HYPERVISOR.*mandatory", reason))
        self.assertRaises(InvalidInputError, self.instance.run)

        self.instance.hypervisor = "esxi"
        self.instance.package = None
        ready, reason = self.instance.ready_to_run()
        self.assertEqual(ready, False)
        self.assertTrue(re.search("PACKAGE.*mandatory", reason))
        self.assertRaises(InvalidInputError, self.instance.run)

    def test_invalid_args(self):
        """Negative testing for various arguments."""
        with self.assertRaises(InvalidInputError):
            self.instance.hypervisor = "frobozz"
        with self.assertRaises(InvalidInputError):
            self.instance.configuration = ""
        with self.assertRaises(InvalidInputError):
            self.instance.configuration = "X"
        with self.assertRaises(InvalidInputError):
            self.instance.network_map = [""]
        with self.assertRaises(InvalidInputError):
            self.instance.network_map = ["foo"]
        with self.assertRaises(InvalidInputError):
            self.instance.network_map = ["=bar"]
        with self.assertRaises(InvalidInputError):
            self.instance.network_map = ["foo="]
