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
from COT.commands import Command, ReadCommand, ReadWriteCommand
from COT.data_validation import InvalidInputError
from COT.vm_description import VMInitError

# pylint: disable=missing-param-doc,missing-type-doc,protected-access


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
    def test_check_disk_space_insufficient(self, mock_available):
        """Negative test for check_disk_space API."""
        # If user declines, return False or die
        self.command.ui.default_confirm_response = False

        self.assertFalse(self.command.check_disk_space(100, self.temp_dir))
        mock_available.assert_called_once()

        mock_available.reset_mock()
        self.command._cached_disk_requirements.clear()
        self.assertRaises(SystemExit, self.command.check_disk_space,
                          100, self.temp_dir, die=True)
        mock_available.assert_called_once()

        mock_available.reset_mock()
        self.command._cached_disk_requirements.clear()

        # If user accepts, return True anyways
        self.command.ui.default_confirm_response = True

        self.assertTrue(self.command.check_disk_space(100, self.temp_dir))
        mock_available.assert_called_once()

        mock_available.reset_mock()
        self.command._cached_disk_requirements.clear()
        self.assertTrue(self.command.check_disk_space(100, self.temp_dir,
                        die=True))
        mock_available.assert_called_once()

    @mock.patch("COT.commands.command.available_bytes_at_path")
    def test_check_disk_space_caching(self, mock_available):
        """Confirm disk space checks are invoked and cached appropriately."""
        mock_available.return_value = 50000

        val = self.command.check_disk_space(100, __file__)
        self.assertTrue(val)
        mock_available.assert_called_once_with(os.path.dirname(__file__))
        mock_available.reset_mock()

        # Checking same path again with different, lower size - no re-check
        val = self.command.check_disk_space(50, __file__)
        self.assertTrue(val)
        mock_available.assert_not_called()

        # Checking the same path again with the same size - no re-check
        val = self.command.check_disk_space(100, __file__)
        self.assertTrue(val)
        mock_available.assert_not_called()

        # As caching is by directory not by file,
        # checking the same directory again with the same size - no re-check
        val = self.command.check_disk_space(100, os.path.dirname(__file__))
        self.assertTrue(val)
        mock_available.assert_not_called()

        # Checking same path with increased size - re-check
        val = self.command.check_disk_space(200, os.path.dirname(__file__))
        self.assertTrue(val)
        mock_available.assert_called_once_with(os.path.dirname(__file__))
        mock_available.reset_mock()

        # Checking different path - re-check
        val = self.command.check_disk_space(100, self.input_ovf)
        self.assertTrue(val)
        mock_available.assert_called_once_with(os.path.dirname(self.input_ovf))
        mock_available.reset_mock()

        # Explictly forcing re-check
        val = self.command.check_disk_space(100, self.input_ovf,
                                            force_check=True)
        self.assertTrue(val)
        mock_available.assert_called_once_with(os.path.dirname(self.input_ovf))
        mock_available.reset_mock()


class TestReadCommand(TestCommand):
    """Test cases for ReadCommand class."""

    command_class = ReadCommand

    def test_set_package_nonexistent(self):
        """Package setter raises InvalidInputError for nonexistent file."""
        with self.assertRaises(InvalidInputError):
            self.command.package = "/foo/bar/baz"

    def test_not_ready_if_insufficient_working_space(self):
        """Verify ready_to_run() fails if working disk space is lacking."""
        self.command.package = self.input_ovf

        self.command.ui.default_confirm_response = False
        with mock.patch.object(self.command,
                               'working_dir_disk_space_required',
                               return_value=(1 << 60)):
            ready, reason = self.command.ready_to_run()

        self.assertFalse(ready)
        self.assertRegex(reason, "Insufficient disk space available for"
                         " temporary file storage")

        # User can opt to continue anyway
        self.command.ui.default_confirm_response = True
        self.command._cached_disk_requirements.clear()
        with mock.patch.object(self.command,
                               'working_dir_disk_space_required',
                               return_value=(1 << 60)):
            ready, reason = self.command.ready_to_run()

        self.assertTrue(ready)


class TestReadWriteCommand(TestReadCommand):
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

    def test_not_ready_if_insufficient_output_space(self):
        """Ensure that ready_to_run() fails if output disk space is lacking."""
        self.command.package = self.input_ovf

        self.command.ui.default_confirm_response = False
        # Make working directory requirements negligible but output huge
        with mock.patch.object(self.command,
                               "working_dir_disk_space_required",
                               return_value=0), \
            mock.patch.object(self.command.vm,
                              'predicted_output_size',
                              return_value=(1 << 60)):
            ready, reason = self.command.ready_to_run()

        self.assertFalse(ready)
        self.assertRegex(reason, "Insufficient disk space available"
                         " to guarantee successful output")

        # User can opt to continue anyway
        self.command.ui.default_confirm_response = True
        self.command._cached_disk_requirements.clear()
        with mock.patch.object(self.command,
                               "working_dir_disk_space_required",
                               return_value=0), \
            mock.patch.object(self.command.vm,
                              'predicted_output_size',
                              return_value=(1 << 60)):
            ready, reason = self.command.ready_to_run()

        self.assertTrue(ready)

    def test_set_output_invalid(self):
        """Check various failure cases for output setter."""
        # Nonexistent output location, regardless of package
        with self.assertRaises(InvalidInputError):
            self.command.output = "/foo/bar/baz"

        self.command.package = self.input_ovf
        # Nonexistent output location with package set
        with self.assertRaises(InvalidInputError):
            self.command.output = "/foo/bar/baz.ova"

        # Output to directory instead of file (currently unsupported)
        with self.assertRaises(InvalidInputError):
            self.command.output = self.temp_dir

        # Output to "directory" under a file
        with self.assertRaises(InvalidInputError):
            self.command.output = os.path.join(self.input_ovf, "foo.ova")

    def test_set_output_implicitly(self):
        """If 'output' is not specifically set, run() sets it to 'package'."""
        self.command.output = ""
        self.command.package = self.input_ovf
        self.assertEqual(self.command.output, "")
        self.command.run()
        self.assertEqual(self.command.output, self.input_ovf)

    def test_finished_no_vm(self):
        """Verify that finished() can be successful if no VM was set."""
        self.command.finished()
