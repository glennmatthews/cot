#!/usr/bin/env python
#
# deploy.py - test cases for the COTDeploy class and helpers
#
# January 2015, Glenn F. Matthews
# Copyright (c) 2013-2017 the COT project developers.
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

import re

from COT.tests import COTTestCase
from COT.commands.tests.command_testcase import CommandTestCase
from COT.commands.deploy import COTDeploy, SerialConnection
from COT.data_validation import InvalidInputError, ValueUnsupportedError


class TestCOTDeploy(CommandTestCase):
    """Test cases for COTDeploy."""

    command_class = COTDeploy

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCOTDeploy, self).setUp()
        self.command.package = self.input_ovf

    def test_not_ready_with_no_args(self):
        """Verify that ready_to_run() is False without all mandatory args."""
        ready, reason = self.command.ready_to_run()
        self.assertEqual(ready, False)
        self.assertTrue(re.search("HYPERVISOR.*mandatory", reason))
        self.assertRaises(InvalidInputError, self.command.run)

        self.command.hypervisor = "esxi"
        self.command.package = None
        ready, reason = self.command.ready_to_run()
        self.assertEqual(ready, False)
        self.assertTrue(re.search("PACKAGE.*mandatory", reason))
        self.assertRaises(InvalidInputError, self.command.run)

    def test_invalid_args(self):
        """Negative testing for various arguments."""
        with self.assertRaises(InvalidInputError):
            self.command.hypervisor = "frobozz"
        with self.assertRaises(InvalidInputError):
            self.command.configuration = ""
        with self.assertRaises(InvalidInputError):
            self.command.configuration = "X"
        with self.assertRaises(InvalidInputError):
            self.command.network_map = [""]
        with self.assertRaises(InvalidInputError):
            self.command.network_map = ["foo"]
        with self.assertRaises(InvalidInputError):
            self.command.network_map = ["=bar"]
        with self.assertRaises(InvalidInputError):
            self.command.network_map = ["foo="]

    def test_run(self):
        """Test the generic run() implementation."""
        self.command.hypervisor = "esxi"
        self.command.serial_connection = ["tcp::22", "tcp::23", "tcp::24"]
        self.command.run()


class TestSerialConnection(COTTestCase):
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
        conn = SerialConnection.from_cli_string('/dev/ttyS0')
        self.assertEqual('device', conn.kind)
        self.assertEqual('/dev/ttyS0', conn.value)
        self.assertEqual({}, conn.options)
        self.assertEqual(str(conn),
                         "<SerialConnection kind: device "
                         "value: /dev/ttyS0 options: {}>")

        conn = SerialConnection.from_cli_string(
            'file:/tmp/foo.txt,datastore=datastore1')
        self.assertEqual('file', conn.kind)
        self.assertEqual('/tmp/foo.txt', conn.value)
        self.assertEqual({'datastore': 'datastore1'}, conn.options)
        self.assertEqual(str(conn),
                         "<SerialConnection kind: file "
                         "value: /tmp/foo.txt "
                         "options: {'datastore': 'datastore1'}>")

        conn = SerialConnection.from_cli_string('tcp::22,server')
        self.assertEqual('tcp', conn.kind)
        self.assertEqual(':22', conn.value)
        self.assertEqual({'server': True}, conn.options)
        self.assertEqual(str(conn),
                         "<SerialConnection kind: tcp value: :22 "
                         "options: {'server': True}>")

        conn = SerialConnection.from_cli_string('telnet://1.1.1.1:1111')
        self.assertEqual('telnet', conn.kind)
        self.assertEqual('1.1.1.1:1111', conn.value)
        self.assertEqual({}, conn.options)
        self.assertEqual(str(conn),
                         "<SerialConnection kind: telnet "
                         "value: 1.1.1.1:1111 options: {}>")
