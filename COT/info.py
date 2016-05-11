#!/usr/bin/env python
#
# info.py - Implements "info" sub-command
#
# October 2013, Glenn F. Matthews
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

"""Implements "info" subcommand."""

import logging
import os.path

from .submodule import COTGenericSubmodule
from .vm_context_manager import VMContextManager
from .data_validation import InvalidInputError

logger = logging.getLogger(__name__)


class COTInfo(COTGenericSubmodule):
    """Display VM information string.

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`

    Attributes:
    :attr:`package_list`,
    :attr:`verbosity`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTInfo, self).__init__(UI)
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

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if not self.package_list:
            return False, "At least one package must be specified"
        return super(COTInfo, self).ready_to_run()

    def run(self):
        """Do the actual work of this submodule.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTInfo, self).run()

        first = True
        for package in self.package_list:
            if not first:
                print("")
            with VMContextManager(package, None) as vm:
                print(vm.info_string(self.UI.terminal_width - 1,
                                     self.verbosity))
            first = False

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        :param object parent: Subparser grouping object returned by
            :meth:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
        p = parent.add_parser(
            'info',
            help="""Generate a description of an OVF package""",
            usage="""
  cot info --help
  cot info [-b | -v] PACKAGE [PACKAGE ...]""",
            description="""
Show a summary of the contents of the given OVF(s) and/or OVA(s).""")

        group = p.add_mutually_exclusive_group()

        group.add_argument('-b', '--brief',
                           action='store_const', const='brief',
                           dest='verbosity',
                           help="""Brief output (shorter)""")
        group.add_argument('-v', '--verbose',
                           action='store_const', const='verbose',
                           dest='verbosity',
                           help="""Verbose output (longer)""")

        p.add_argument('PACKAGE_LIST',
                       nargs='+',
                       metavar='PACKAGE [PACKAGE ...]',
                       help="OVF descriptor(s) and/or OVA file(s) to describe")
        p.set_defaults(instance=self)

        storage['info'] = p
