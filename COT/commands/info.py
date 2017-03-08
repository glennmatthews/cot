#!/usr/bin/env python
#
# info.py - Implements "info" sub-command
#
# October 2013, Glenn F. Matthews
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

"""Implements "info" subcommand."""

from __future__ import print_function

import logging
import os.path

from COT.vm_description import VMDescription, VMInitError
from COT.data_validation import InvalidInputError
from .command import command_classes, Command

logger = logging.getLogger(__name__)


class COTInfo(Command):
    """Display VM information string.

    Inherited attributes:
    :attr:`~Command.ui`

    Attributes:
    :attr:`package_list`,
    :attr:`verbosity`
    """

    def __init__(self, ui):
        """Instantiate this command with the given UI.

        Args:
          ui (UI): User interface instance.
        """
        super(COTInfo, self).__init__(ui)
        self._package_list = None
        self._verbosity = None

    @property
    def package_list(self):
        """List of VM definitions to get information for."""
        return self._package_list

    @package_list.setter
    def package_list(self, value):
        for package in value:
            if not os.path.exists(package):
                raise InvalidInputError("Specified package {0} does not exist!"
                                        .format(package))
        self._package_list = value

    @property
    def verbosity(self):
        """Verbosity of information displayed."""
        return self._verbosity

    @verbosity.setter
    def verbosity(self, value):
        if value not in ['brief', 'verbose', None]:
            raise InvalidInputError(
                "Verbosity must be 'brief', 'verbose', or None")
        self._verbosity = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        Returns:
          tuple: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if not self.package_list:
            return False, "At least one package must be specified"
        return super(COTInfo, self).ready_to_run()

    def run(self):
        """Do the actual work of this command.

        Raises:
          InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTInfo, self).run()

        first = True
        # TODO: UI should provide an "output" method or similar,
        #       so that we don't call print directly here.
        for package in self.package_list:
            if not first:
                print("")
            try:
                with VMDescription.factory(package, None) as vm:
                    print(vm.info_string(self.ui.terminal_width - 1,
                                         self.verbosity))
            except VMInitError as exc:
                logger.error("Unable to display information for %s: %s",
                             package, exc.strerror)
            first = False

    def create_subparser(self):
        """Create 'info' CLI subparser."""
        parser = self.ui.add_subparser(
            'info',
            aliases=['describe'],
            help="""Generate a description of an OVF package""",
            usage="""
  cot info --help
  cot info [-b | -v] PACKAGE [PACKAGE ...]""",
            description="""
Show a summary of the contents of the given OVF(s) and/or OVA(s).""")

        group = parser.add_mutually_exclusive_group()

        group.add_argument('-b', '--brief',
                           action='store_const', const='brief',
                           dest='verbosity',
                           help="""Brief output (shorter)""")
        group.add_argument('-v', '--verbose',
                           action='store_const', const='verbose',
                           dest='verbosity',
                           help="""Verbose output (longer)""")

        parser.add_argument(
            'PACKAGE_LIST', nargs='+', metavar='PACKAGE [PACKAGE ...]',
            help="OVF descriptor(s) and/or OVA file(s) to describe")
        parser.set_defaults(instance=self)


command_classes.append(COTInfo)
