#!/usr/bin/env python
#
# ui_shared.py - abstraction between CLI and GUI
#
# December 2014, Glenn F. Matthews
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
import sys
import textwrap

# VerboseLogger adds a log level 'verbose' between 'info' and 'debug'.
# This lets us be a bit more fine-grained in our logging verbosity.
from verboselogs import VerboseLogger
logging.setLoggerClass(VerboseLogger)
logger = logging.getLogger(__name__)


class UI(object):
    """Abstract user interface functionality.
    Can also be used in test code as a stub that autoconfirms everything."""

    def __init__(self, force=False):
        self.force = force
        # Stub for API testing
        self.default_confirm_response = True
        self.textwrap = textwrap.TextWrapper()

    def fill(self, text, **kwargs):
        """Wrap the given text if appropriate to this UI."""
        self.textwrap.width = self.terminal_width() - 1
        for (arg, value) in kwargs.items():
            self.textwrap.__dict__[arg] = value
        return self.textwrap.fill(text)

    def terminal_width(self):
        """Returns the width of the terminal in columns."""
        return 80

    def fill_usage(self, subcommand, usage_list):
        """Pretty-print a list of usage strings."""
        return "\n".join(["{0} {1}".format(subcommand, usage)
                          for usage in usage_list])

    def fill_examples(self, example_list):
        """Pretty-print a set of usage examples.
        example_list == [(example1, desc1), (example2, desc2), ...]
        """
        raise NotImplementedError("No implementation for fill_examples()")

    def confirm(self, prompt):
        """Prompts user to confirm the requested operation, or auto-accepts
        if 'force' is set to True."""
        if self.force:
            logger.warning("Automatically agreeing to '{0}'".format(prompt))
            return True
        return self.default_confirm_response

    def confirm_or_die(self, prompt):
        """If the user doesn't agree, abort!"""
        if not self.confirm(prompt):
            sys.exit("Aborting.")

    def get_input(self, prompt, default_value):
        """Prompt the user to enter a string, or auto-accepts the default
        if 'force' is set to True."""
        if self.force:
            logger.warning("Automatically entering {0} in response to '{1}'"
                           .format(default_value, prompt))
            return default_value
        return default_value

    def get_password(self, username, host):
        """Get password string from the user."""
        return "passwd"
