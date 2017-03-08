#!/usr/bin/env python
#
# command_testcase.py - base class for Command test cases
#
# March 2017, Glenn F. Matthews
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

"""Base unit test case class for testing of COT Command classes."""

import logging
import traceback

import mock

try:
    # Python 2.x
    import StringIO
except ImportError:
    # Python 3.x
    import io as StringIO

from COT.tests import COTTestCase
from COT.ui import UI
from COT.utilities import directory_size, pretty_bytes
from COT.commands import Command, ReadWriteCommand

logger = logging.getLogger(__name__)

# pylint: disable=missing-param-doc,protected-access


class CommandTestCase(COTTestCase):
    """Base class for COT Command class test cases."""

    command_class = Command
    """Command subclass to instantiate for each test step."""

    # WARNING logger messages we may expect at various points
    # TODO: change these to functions so we can populate 'args' for each
    DRIVE_TYPE_GUESSED_HARDDISK = {
        'levelname': 'WARNING',
        'msg': "drive type not specified.*guessing.*based on file extension",
        'args': ('harddisk', ),
    }
    DRIVE_TYPE_GUESSED_CDROM = {
        'levelname': 'WARNING',
        'msg': "drive type not specified.*guessing.*based on file extension",
        'args': ('cdrom', ),
    }
    CONTROLLER_TYPE_GUESSED_IDE = {
        'levelname': 'WARNING',
        'msg': "Controller type not specified - guessing.*based on disk drive",
        'args': ('ide', r'.*', r'.*'),
    }
    OVERWRITING_FILE = {
        'levelname': 'NOTICE',
        'msg': "Overwriting existing File in OVF",
    }
    OVERWRITING_DISK = {
        'levelname': 'NOTICE',
        'msg': "Overwriting existing Disk in OVF",
    }
    OVERWRITING_DISK_ITEM = {
        'levelname': 'NOTICE',
        'msg': "Overwriting existing disk Item in OVF",
    }

    def setUp(self):
        """Test case setup function called automatically before each test."""
        super(CommandTestCase, self).setUp()
        self.command = self.command_class(UI())
        if isinstance(self.command, ReadWriteCommand):
            self.command._output = self.temp_file

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        if self.command:
            # Check instance working directory prediction against reality
            if self.command.vm:
                estimate = self.command.working_dir_disk_space_required()
                actual = directory_size(self.command.vm.working_dir)
                if estimate < actual:
                    self.fail("Estimated {0} would be needed in working"
                              " directory, but VM actually used {1}"
                              .format(pretty_bytes(estimate),
                                      pretty_bytes(actual)))

            self.command.destroy()
            self.command = None

        super(CommandTestCase, self).tearDown()

    def set_vm_platform(self, plat_class):
        """Force the VM under test to use a particular Platform class.

        Args:
           plat_class (COT.platforms.Platform): Platform class to use
        """
        # pylint: disable=protected-access
        self.command.vm._platform = plat_class()

    def check_cot_output(self, expected):
        """Grab the output from COT and check it against expected output.

        Args:
          expected (str): Expected output
        Raises:
          AssertionError: if an error is raised by COT when run
          AssertionError: if the output returned does not match expected.
        """
        with mock.patch('sys.stdout',
                        new_callable=StringIO.StringIO) as stdout:
            try:
                self.command.run()
            except (TypeError, ValueError, SyntaxError, LookupError):
                self.fail(traceback.format_exc())
            output = stdout.getvalue()
        self.maxDiff = None
        self.assertMultiLineEqual(expected.strip(), output.strip())
