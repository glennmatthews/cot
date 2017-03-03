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

from COT.tests.ut import COT_UT
from COT.ui import UI
from COT.utilities import directory_size, pretty_bytes

logger = logging.getLogger(__name__)

# pylint: disable=missing-param-doc


class CommandTestCase(COT_UT):
    """Base class for COT Command class test cases."""

    command_class = None
    """Command subclass to instantiate for each test step."""

    # WARNING logger messages we may expect at various points
    # TODO: change these to functions so we can populate 'args' for each
    TYPE_NOT_SPECIFIED_GUESS_HARDDISK = {
        'levelname': 'WARNING',
        'msg': "drive type not specified.*guessing.*based on file extension",
        'args': ('harddisk', ),
    }
    TYPE_NOT_SPECIFIED_GUESS_CDROM = {
        'levelname': 'WARNING',
        'msg': "drive type not specified.*guessing.*based on file extension",
        'args': ('cdrom', ),
    }
    CONTROLLER_NOT_SPECIFIED_GUESS_IDE = {
        'levelname': 'WARNING',
        'msg': "Guessing controller type.*based on disk drive type",
        'args': ('ide', r'.*', r'.*'),
    }
    OVERWRITING_FILE = {
        'levelname': 'WARNING',
        'msg': "Overwriting existing File in OVF",
    }
    OVERWRITING_DISK = {
        'levelname': 'WARNING',
        'msg': "Overwriting existing Disk in OVF",
    }
    OVERWRITING_DISK_ITEM = {
        'levelname': 'WARNING',
        'msg': "Overwriting existing disk Item in OVF",
    }

    def __init__(self, *args, **kwargs):
        """Add command instance to generic UT initialization.

        For the parameters, see :class:`unittest.TestCase`.
        """
        super(CommandTestCase, self).__init__(*args, **kwargs)
        if self.__class__.command_class is not None:
            # pylint: disable=not-callable
            self.instance = self.__class__.command_class(UI())
        else:
            self.instance = None

    def set_vm_platform(self, plat_class):
        """Force the VM under test to use a particular Platform class.

        Args:
           plat_class (COT.platforms.Platform): Platform class to use
        """
        # pylint: disable=protected-access
        self.instance.vm._platform = plat_class()

    def check_cot_output(self, expected):
        """Grab the output from COT and check it against expected output.

        Args:
          expected (str): Expected output
        Raises:
          AssertionError: if an error is raised by COT when run
          AssertionError: if the output returned does not match expected.
        """
        with mock.patch('sys.stdout', new_callable=StringIO.StringIO) as so:
            try:
                self.instance.run()
            except (TypeError, ValueError, SyntaxError, LookupError):
                self.fail(traceback.format_exc())
            output = so.getvalue()
        self.maxDiff = None
        self.assertMultiLineEqual(expected.strip(), output.strip())

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        if self.instance:
            # Check instance working directory prediction against reality
            if self.instance.vm:
                estimate = self.instance.working_dir_disk_space_required()
                actual = directory_size(self.instance.vm.working_dir)
                if estimate < actual:
                    self.fail("Estimated {0} would be needed in working"
                              " directory, but VM actually used {1}"
                              .format(pretty_bytes(estimate),
                                      pretty_bytes(actual)))

            self.instance.destroy()
            self.instance = None

        super(CommandTestCase, self).tearDown()
