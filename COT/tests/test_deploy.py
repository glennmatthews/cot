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
from COT.deploy import COTDeploy, SerialConnection
from COT.data_validation import InvalidInputError, ValueUnsupportedError

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

    def test_run(self):
        """Test the generic run() implementation."""
        self.instance.hypervisor = "esxi"
        self.instance.serial_connection = ["tcp::22", "tcp::23", "tcp::24"]
        self.instance.run()


class TestSerialConnection(COT_UT):
    """Unit test cases for SerialConnection class."""

    def test_from_cli_string_invalid(self):
        """Negative tests for SerialConnection.from_cli_string() method."""
        # Parsing failure
        self.assertRaises(InvalidInputError,
                          SerialConnection.from_cli_string, ',bar')
        # Parsing succeeds but invalid kind
        self.assertRaises(ValueUnsupportedError,
                          SerialConnection.from_cli_string, 'foo:bar')
        # Parsing succeeds but invalid value
        self.assertRaises(InvalidInputError,
                          SerialConnection.from_cli_string, 'tcp:bar')
        # Parsing succeeds but incorrect options
        self.assertRaises(InvalidInputError,
                          SerialConnection.from_cli_string,
                          'file:/tmp/foo.txt')
        self.assertEqual(None, SerialConnection.from_cli_string("   "))

    def test_from_cli_string_valid(self):
        """Positive tests for SerialConnection.from_cli_string()."""
        c = SerialConnection.from_cli_string('/dev/ttyS0')
        self.assertEqual('device', c.kind)
        self.assertEqual('/dev/ttyS0', c.value)
        self.assertEqual({}, c.options)

        c = SerialConnection.from_cli_string(
            'file:/tmp/foo.txt,datastore=datastore1')
        self.assertEqual('file', c.kind)
        self.assertEqual('/tmp/foo.txt', c.value)
        self.assertEqual({'datastore': 'datastore1'}, c.options)

        c = SerialConnection.from_cli_string('tcp::22,server')
        self.assertEqual('tcp', c.kind)
        self.assertEqual(':22', c.value)
        self.assertEqual({'server': True}, c.options)

        c = SerialConnection.from_cli_string('telnet://1.1.1.1:1111')
        self.assertEqual('telnet', c.kind)
        self.assertEqual('1.1.1.1:1111', c.value)
        self.assertEqual({}, c.options)
