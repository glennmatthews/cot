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

import logging
import os.path

from .submodule import COTReadOnlySubmodule
from .vm_context_manager import VMContextManager

logger = logging.getLogger(__name__)


class COTInfo(COTReadOnlySubmodule):
    """Display VM information string"""
    def __init__(self, UI):
        super(COTInfo, self).__init__(
            UI,
            [
                "PACKAGE_LIST",
                "verbosity",
            ])

    def validate_arg(self, arg, value):
        valid, value_or_reason = super(COTInfo, self).validate_arg(arg, value)
        if not valid or value_or_reason is None:
            return valid, value_or_reason
        value = value_or_reason

        if arg == "PACKAGE_LIST":
            for package in value:
                if not os.path.exists(package):
                    return False, ("Specified package {0} does not exist!"
                                   .format(package))
        elif arg == "verbosity":
            if value not in ['brief', 'verbose', None]:
                return False, "Verbosity must be 'brief', 'verbose', or None"

        return valid, value_or_reason

    def ready_to_run(self):
        """Are we ready to go?
        Returns the tuple (ready, reason)
        """
        if not self.get_value("PACKAGE_LIST"):
            return False, "At least one package must be specified"
        return super(COTInfo, self).ready_to_run()

    def run(self):
        super(COTInfo, self).run()

        PACKAGE_LIST = self.get_value("PACKAGE_LIST")
        verbosity = self.get_value("verbosity")
        first = True
        for package in PACKAGE_LIST:
            if not first:
                print("")
            with VMContextManager(package, None) as vm:
                print(vm.info_string(self.UI.terminal_width() - 1, verbosity))
            first = False

    def create_subparser(self, parent):
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

        return 'info', p
