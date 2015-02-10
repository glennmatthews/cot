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

import logging

from .submodule import COTGenericSubmodule

logger = logging.getLogger(__name__)


class COTHelp(COTGenericSubmodule):
    """Provide 'help <subcommand>' syntax"""
    def __init__(self, UI):
        super(COTHelp, self).__init__(UI, ["SUBCOMMAND"])

    def validate_arg(self, arg, value):
        valid, value_or_reason = super(COTHelp, self).validate_arg(arg, value)
        if not valid or value_or_reason is None:
            return valid, value_or_reason
        if arg == "SUBCOMMAND":
            valid_cmds = sorted(self.UI.subparser_lookup.keys())
            if value not in valid_cmds:
                return False, ("Invalid command '{0}' (choose from '{1}')"
                               .format(value, "', '".join(valid_cmds)))

        return True, value_or_reason

    def run(self):
        super(COTHelp, self).run()

        command = self.get_value("SUBCOMMAND")
        if command:
            subp = self.UI.subparser_lookup[command]
            subp.print_help()
        else:
            self.UI.parser.print_help()

    def create_subparser(self, parent):
        p = parent.add_parser(
            'help',
            add_help=False,
            help="""Print help for a command""",
            usage="""
  cot help <command>""",
            description="Display help message for the given command")

        p.add_argument("SUBCOMMAND", metavar="<command>", nargs='?',
                       help=", ".join(sorted(self.UI.subparser_lookup.keys())))

        p.set_defaults(instance=self)

        return 'help', p
