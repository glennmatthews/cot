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

"""Abstract user interface superclass."""

import logging
import sys

# VerboseLogger adds a log level 'verbose' between 'info' and 'debug'.
# This lets us be a bit more fine-grained in our logging verbosity.
from verboselogs import VerboseLogger
logging.setLoggerClass(VerboseLogger)
logger = logging.getLogger(__name__)


class UI(object):
    """Abstract user interface functionality.

    Can also be used in test code as a stub that autoconfirms everything.
    """

    def __init__(self, force=False):
        """Constructor."""
        self.force = force
        """Whether to automatically select the default value in all cases.

        (As opposed to interactively prompting the user.)
        """
        self.default_confirm_response = True
        """Knob for API testing, sets the default response to confirm()."""
        self._terminal_width = 80
        import COT.helpers.helper
        COT.helpers.helper.confirm = self.confirm

    @property
    def terminal_width(self):
        """Get the width of the terminal in columns."""
        return self._terminal_width

    def fill_usage(self, subcommand, usage_list):
        """Pretty-print a list of usage strings.

        :param str subcommand: Subcommand name/keyword
        :param list usage_list: List of usage strings for this subcommand.
        :returns: String containing all usage strings, each appropriately
            wrapped to the :attr:`terminal_width` value.
        """
        return "\n".join(["{0} {1}".format(subcommand, usage)
                          for usage in usage_list])

    def fill_examples(self, example_list):
        """Pretty-print a set of usage examples.

        :param list example_list: List of (example, description) tuples.
        :raise NotImplementedError: Must be implemented by a subclass.
        """
        raise NotImplementedError("No implementation for fill_examples()")

    def confirm(self, prompt):
        """Prompt user to confirm the requested operation.

        Auto-accepts if :attr:`force` is set to ``True``.

        .. warning::
          This stub implementation does not actually interact with the user,
          but instead returns :attr:`default_confirm_response`. Subclasses
          should override this method.

        :param str prompt: Message to prompt the user with
        :return: ``True`` (user confirms acceptance) or ``False``
            (user declines)
        """
        if self.force:
            logger.warning("Automatically agreeing to '{0}'".format(prompt))
            return True
        return self.default_confirm_response

    def confirm_or_die(self, prompt):
        """If the user doesn't agree, abort the program.

        A simple wrapper for :meth:`confirm` that calls :func:`sys.exit` if
        :meth:`confirm` returns ``False``.
        """
        if not self.confirm(prompt):
            sys.exit("Aborting.")

    def choose_from_list(self, footer, option_list, default_value,
                         header="", info_list=[]):
        """Prompt the user to choose from a list.

        :param footer: Prompt string to display following the list
        :param option_list: List of strings to choose amongst
        :param default_value: Default value to select if user declines
        :param header: String to display prior to the list
        :param info_list: Verbose strings to display instead of option_list
        """
        if not info_list:
            info_list = option_list
        prompt_list = [header] + ["""{0:2}) {1}""".format(i, inf.strip())
                                  for i, inf in enumerate(info_list, start=1)]
        prompt_list.append(footer)
        prompt = "\n".join(prompt_list)
        while True:
            result = self.get_input(prompt, default_value)

            # Exact match or user declined to choose
            if result == default_value or result in option_list:
                return result
            # Unique prefix match
            match = [opt for opt in option_list if opt.startswith(result)]
            if len(match) == 1:
                return match[0]
            # Did user enter a list index?
            try:
                i = int(result)
                return option_list[i-1]
            except (ValueError, IndexError):
                pass
            logger.error("Invalid input. Please try again.")

    def get_input(self, prompt, default_value):
        """Prompt the user to enter a string.

        Auto-inputs the :attr:`default_value` if :attr:`force` is set to
        ``True``.

        .. warning::
          This stub implementation does not actually interact with the user,
          but instead always returns :attr:`default_value`. Subclasses should
          override this method.

        :param str prompt: Message to prompt the user with
        :param str default_value: Default value to input if the user simply
            hits Enter without entering a value, or if :attr:`force`.

        :return: Input value
        :rtype: str
        """
        if self.force:
            logger.warning("Automatically entering {0} in response to '{1}'"
                           .format(default_value, prompt))
            return default_value
        return default_value

    def get_password(self, username, host):
        """Get password string from the user.

        .. warning::
          This stub implementation does not actually interact with the user,
          but instead always returns ``"passwd"``. Subclasses should override
          this method.

        :param str username: Username the password is associated with
        :param str host: Host the password is associated with
        """
        return "passwd"
