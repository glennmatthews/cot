#!/usr/bin/env python
#
# test_command.py - test cases for the generic ReadWriteCommand class
#
# January 2015, Glenn F. Matthews
# Copyright (c) 2015-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Test cases for COT.commands.ReadWriteCommand class."""

import os.path
import mock

from COT.commands.tests.command_testcase import CommandTestCase
from COT.ui import UI
from COT.commands import ReadWriteCommand
from COT.vm_description import VMInitError

# pylint: disable=missing-param-doc,missing-type-doc


class TestReadWriteCommand(CommandTestCase):
    """Test cases for ReadWriteCommand class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestReadWriteCommand, self).setUp()
        self.instance = ReadWriteCommand(UI())
        self.instance.output = self.temp_file

    def test_vmfactory_fail(self):
        """If package/output are unsupported, expect a VMInitError."""
        self.instance.output = "foo.vmx"
        with self.assertRaises(VMInitError):
            self.instance.package = self.input_ovf

    def test_create_subparser_noop(self):
        """The generic class doesn't create a subparser."""
        self.instance.create_subparser()

    def test_set_output_implicitly(self):
        """If 'output' is not specifically set, run() sets it to 'package'."""
        self.instance.output = ""
        self.instance.package = self.input_ovf
        self.assertEqual(self.instance.output, "")
        self.instance.run()
        self.assertEqual(self.instance.output, self.input_ovf)

    @mock.patch("COT.vm_description.ovf.OVF.predicted_output_size")
    @mock.patch("COT.commands.command.available_bytes_at_path")
    def test_space_checks_called(self, mock_available, mock_size):
        """Confirm that disk space checks are invoked appropriately."""
        mock_size.return_value = 10000
        mock_available.return_value = 50000

        # Cases that do not result in a check:
        # 1. Set package without setting output
        self.instance = ReadWriteCommand(UI())
        self.instance.package = self.input_ovf

        mock_size.assert_not_called()
        mock_available.assert_not_called()
        self.instance.destroy()

        # 2. Set output without setting package
        self.instance = ReadWriteCommand(UI())
        self.instance.output = self.temp_file
        mock_size.assert_not_called()
        mock_available.assert_not_called()

        self.instance.destroy()
        mock_size.reset_mock()
        mock_available.reset_mock()

        # Cases that do result in a check:
        # 1. Setting package when output is already set
        self.instance = ReadWriteCommand(UI())
        self.instance.output = self.temp_file
        self.instance.package = self.input_ovf
        self.assertNotEqual(self.instance.vm, None)
        mock_size.assert_called_once()
        mock_available.assert_called_once()

        self.instance.destroy()
        mock_size.reset_mock()
        mock_available.reset_mock()

        # 2. Setting output when package is already set
        self.instance = ReadWriteCommand(UI())
        self.instance.package = self.input_ovf
        self.instance.output = self.temp_file
        self.assertNotEqual(self.instance.vm, None)
        mock_size.assert_called_once()
        mock_available.assert_called_once()

        mock_size.reset_mock()
        mock_available.reset_mock()

        # 3. Changing output when package is already set
        self.instance.output = os.path.join(self.temp_dir, "new_out.ovf")
        mock_size.assert_called_once()
        mock_available.assert_called_once()

        mock_size.reset_mock()
        mock_available.reset_mock()
