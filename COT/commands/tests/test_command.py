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

"""Test cases for COT.commands.Command class and generic subclasses."""

import os.path
import mock

from COT.commands.tests.command_testcase import CommandTestCase
from COT.ui import UI
from COT.commands import Command, ReadCommand, ReadWriteCommand
from COT.data_validation import InvalidInputError
from COT.vm_description import VMInitError

# pylint: disable=missing-param-doc,missing-type-doc


class TestCommand(CommandTestCase):
    """Test cases for Command base class."""

    command_class = Command

    def test_disk_space_required_zero_if_no_vm(self):
        """Corner case - no VM yet, working_dir_disk_space_required == 0."""
        self.assertEqual(self.command.working_dir_disk_space_required(), 0)

    def test_check_disk_space_sufficient(self):
        """Positive test for check_disk_space API."""
        self.assertTrue(self.command.check_disk_space(1, self.temp_dir))
        self.assertTrue(self.command.check_disk_space(
            1, self.temp_dir,
            label="Hello", context="Contextual detail", die=True))

    @mock.patch("COT.commands.command.available_bytes_at_path", return_value=0)
    def test_check_disk_space_insufficient(self, *_):
        """Negative test for check_disk_space API."""
        # If user declines, return False or die
        self.command.ui.default_confirm_response = False
        self.assertFalse(self.command.check_disk_space(100, self.temp_dir))
        self.assertRaises(SystemExit, self.command.check_disk_space,
                          100, self.temp_dir, die=True)

        # If user accepts, return True anyways
        self.command.ui.default_confirm_response = True
        self.assertTrue(self.command.check_disk_space(100, self.temp_dir))
        self.assertTrue(self.command.check_disk_space(100, self.temp_dir,
                        die=True))


class TestReadCommand(CommandTestCase):
    """Test cases for ReadCommand class."""

    command_class = ReadCommand

    def test_set_package_nonexistent(self):
        """Package setter raises InvalidInputError for nonexistent file."""
        with self.assertRaises(InvalidInputError):
            self.command.package = "/foo/bar/baz"

    def test_not_ready_if_insufficient_space(self):
        """Ensure that ready_to_run() fails if disk space is lacking."""
        self.command.package = self.input_ovf

        self.command.ui.default_confirm_response = False
        with mock.patch.object(self.command,
                               'working_dir_disk_space_required',
                               return_value=(1 << 60)):
            ready, reason = self.command.ready_to_run()

        self.assertFalse(ready)
        self.assertRegex(reason, "Insufficient disk space available")

        # User can opt to continue anyway
        self.command.ui.default_confirm_response = True
        with mock.patch.object(self.command,
                               'working_dir_disk_space_required',
                               return_value=(1 << 60)):
            ready, reason = self.command.ready_to_run()

        self.assertTrue(ready)


class TestReadWriteCommand(CommandTestCase):
    """Test cases for ReadWriteCommand class."""

    command_class = ReadWriteCommand

    def test_vmfactory_fail(self):
        """If package/output are unsupported, expect a VMInitError."""
        self.command.output = "foo.vmx"
        with self.assertRaises(VMInitError):
            self.command.package = self.input_ovf

    def test_create_subparser_noop(self):
        """The generic class doesn't create a subparser."""
        self.command.create_subparser()

    def test_set_output_implicitly(self):
        """If 'output' is not specifically set, run() sets it to 'package'."""
        self.command.output = ""
        self.command.package = self.input_ovf
        self.assertEqual(self.command.output, "")
        self.command.run()
        self.assertEqual(self.command.output, self.input_ovf)

    @mock.patch("COT.vm_description.ovf.OVF.predicted_output_size")
    @mock.patch("COT.commands.command.available_bytes_at_path")
    def test_space_checks_called(self, mock_available, mock_size):
        """Confirm that disk space checks are invoked appropriately."""
        mock_size.return_value = 10000
        mock_available.return_value = 50000

        # Cases that do not result in a check:
        # 1. Set package without setting output
        self.command = ReadWriteCommand(UI())
        self.command.package = self.input_ovf
        mock_size.assert_not_called()
        mock_available.assert_not_called()

        # Unset package
        self.command.package = None
        mock_size.assert_not_called()
        mock_available.assert_not_called()

        # 2. Set output without setting package
        self.command = ReadWriteCommand(UI())
        self.command.output = self.temp_file
        mock_size.assert_not_called()
        mock_available.assert_not_called()

        # Cases that do result in a check:
        # 1. Setting package when output is already set
        self.command.package = self.input_ovf
        self.assertNotEqual(self.command.vm, None)
        mock_size.assert_called_once()
        mock_available.assert_called_once()

        self.command.destroy()
        mock_size.reset_mock()
        mock_available.reset_mock()

        # 2. Setting output when package is already set
        self.command = ReadWriteCommand(UI())
        self.command.package = self.input_ovf
        self.command.output = self.temp_file
        self.assertNotEqual(self.command.vm, None)
        mock_size.assert_called_once()
        mock_available.assert_called_once()

        mock_size.reset_mock()
        mock_available.reset_mock()

        # 3. Changing output when package is already set
        self.command.output = os.path.join(self.temp_dir, "new_out.ovf")
        mock_size.assert_called_once()
        mock_available.assert_called_once()

        mock_size.reset_mock()
        mock_available.reset_mock()

    def test_finished_no_vm(self):
        """Verify that finished() can be successful if no VM was set."""
        self.command.finished()
