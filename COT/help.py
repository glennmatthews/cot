#!/usr/bin/env python
#
# help.py - Submodule for 'help' keyword
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2014-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Provide 'help' keyword for COT CLI."""

import logging

from .submodule import COTGenericSubmodule
from .data_validation import InvalidInputError

logger = logging.getLogger(__name__)


class COTHelp(COTGenericSubmodule):
    """Provide 'help <subcommand>' syntax.

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`

    Attributes:
    :attr:`subcommand`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTHelp, self).__init__(UI)
        self._subcommand = None

    @property
    def subcommand(self):
        """CLI subcommand to give help for.

        If ``None``, then help will be displayed for the COT global parser.
        """
        return self._subcommand

    @subcommand.setter
    def subcommand(self, value):
        valid_cmds = sorted(self.UI.subparser_lookup.keys())
        if value is not None and value not in valid_cmds:
            raise InvalidInputError("Invalid command '{0}' (choose from '{1}')"
                                    .format(value, "', '".join(valid_cmds)))
        self._subcommand = value

    def run(self):
        """Display the help menu for the specified subcommand."""
        super(COTHelp, self).run()

        if self.subcommand:
            subp = self.UI.subparser_lookup[self.subcommand]
            subp.print_help()
        else:
            self.UI.parser.print_help()

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        :param object parent: Subparser grouping object returned by
            :func:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
        p = parent.add_parser(
            'help',
            help="""Print help for a command""",
            usage="""
  cot help <command>""",
            description="Display help message for the given command")

        p.add_argument("SUBCOMMAND", metavar="<command>", nargs='?',
                       help="COT subcommand to display")

        p.set_defaults(instance=self)

        storage['help'] = p
