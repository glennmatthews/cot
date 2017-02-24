#!/usr/bin/env python
#
# ui_shared.py - abstraction between CLI and GUI
#
# December 2014, Glenn F. Matthews
# Copyright (c) 2014-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Generic user interface functions and abstract user interface superclass.

**Functions**

.. autosummary::
  :nosignatures:

  pretty_bytes
  to_string

**Classes**

.. autosummary::
  :nosignatures:

  UI
"""

import logging
import sys
import xml.etree.ElementTree as ET

from verboselogs import VerboseLogger

# VerboseLogger adds a log level 'verbose' between 'info' and 'debug'.
# This lets us be a bit more fine-grained in our logging verbosity.
logging.setLoggerClass(VerboseLogger)
logger = logging.getLogger(__name__)


def to_string(obj):
    """Get string representation of an object, special-case for XML Element.

    Args:
      obj (object): Object to represent as a string.
    Returns:
      str: string representation
    Examples:
      ::

        >>> to_string("Hello")
        'Hello'
        >>> to_string(27.5)
        '27.5'
        >>> e = ET.Element('hello', attrib={'key': 'value'})
        >>> print(e)   # doctest: +ELLIPSIS
        <Element ...hello... at ...>
        >>> print(to_string(e))
        <hello key="value" />
    """
    if ET.iselement(obj):
        if sys.version_info[0] >= 3:
            return ET.tostring(obj, encoding='unicode')
        else:
            return ET.tostring(obj)
    else:
        return str(obj)


def pretty_bytes(byte_value, base_shift=0):
    """Pretty-print the given bytes value.

    Args:
      byte_value (float): Value
      base_shift (int): Base value of byte_value
            (0 = bytes, 1 = KiB, 2 = MiB, etc.)

    Returns:
      str: Pretty-printed byte string such as "1.00 GiB"

    Examples:
      ::

        >>> pretty_bytes(512)
        '512 B'
        >>> pretty_bytes(512, 2)
        '512 MiB'
        >>> pretty_bytes(65536, 2)
        '64 GiB'
        >>> pretty_bytes(65547)
        '64.01 KiB'
        >>> pretty_bytes(65530, 3)
        '63.99 TiB'
        >>> pretty_bytes(1023850)
        '999.9 KiB'
        >>> pretty_bytes(1024000)
        '1000 KiB'
        >>> pretty_bytes(1048575)
        '1024 KiB'
        >>> pretty_bytes(1049200)
        '1.001 MiB'
        >>> pretty_bytes(2560)
        '2.5 KiB'
        >>> pretty_bytes(.0001, 3)
        '104.9 KiB'
        >>> pretty_bytes(.01, 1)
        '10 B'
        >>> pretty_bytes(.001, 1)
        '1 B'
        >>> pretty_bytes(.0001, 1)
        '0 B'
        >>> pretty_bytes(100, -1)
        Traceback (most recent call last):
            ...
        ValueError: base_shift must not be negative
    """
    if base_shift < 0:
        raise ValueError("base_shift must not be negative")
    tags = ["B", "KiB", "MiB", "GiB", "TiB"]
    byte_value = float(byte_value)
    shift = base_shift
    while byte_value >= 1024.0:
        byte_value /= 1024.0
        shift += 1
    while byte_value < 1.0 and shift > 0:
        byte_value *= 1024.0
        shift -= 1
    # Fractions of a byte should be considered a rounding error:
    if shift == 0:
        byte_value = round(byte_value)
    return "{0:.4g} {1}".format(byte_value, tags[shift])


class UI(object):
    """Abstract user interface functionality.

    Can also be used in test code as a stub that autoconfirms everything.
    """

    def __init__(self, force=False):
        """Constructor.

        Args:
          force (bool): See :attr:`force`.
        """
        self.force = force
        """Whether to automatically select the default value in all cases.

        (As opposed to interactively prompting the user.)
        """
        self.default_confirm_response = True
        """Knob for API testing, sets the default response to confirm()."""
        self._terminal_width = 80
        from COT.helpers import Helper
        Helper.USER_INTERFACE = self

    @property
    def terminal_width(self):
        """Get the width of the terminal in columns."""
        return self._terminal_width

    def fill_usage(self,   # pylint: disable=no-self-use
                   subcommand, usage_list):
        """Pretty-print a list of usage strings.

        Args:
          subcommand (str): Subcommand name/keyword
          usage_list (list): List of usage strings for this subcommand.
        Returns:
          str: Concatenation of all usage strings, each appropriately wrapped
          to the :attr:`terminal_width` value.
        """
        return "\n".join(["{0} {1}".format(subcommand, usage)
                          for usage in usage_list])

    def fill_examples(self, example_list):
        """Pretty-print a set of usage examples.

        Args:
          example_list (list): List of (example, description) tuples.
        Raises:
          NotImplementedError: Must be implemented by a subclass.
        """
        raise NotImplementedError("No implementation for fill_examples()")

    def confirm(self, prompt):
        """Prompt user to confirm the requested operation.

        Auto-accepts if :attr:`force` is set to ``True``.

        .. warning::
          This stub implementation does not actually interact with the user,
          but instead returns :attr:`default_confirm_response`. Subclasses
          should override this method.

        Args:
          prompt (str): Message to prompt the user with
        Returns:
          bool: ``True`` (user confirms acceptance) or ``False``
          (user declines)
        """
        if self.force:
            logger.warning("Automatically agreeing to '%s'", prompt)
            return True
        return self.default_confirm_response

    def confirm_or_die(self, prompt):
        """If the user doesn't agree, abort the program.

        A simple wrapper for :meth:`confirm` that calls :func:`sys.exit` if
        :meth:`confirm` returns ``False``.

        Args:
          prompt (str): Message to prompt the user with
        Raises:
          SystemExit: if user declines
        """
        if not self.confirm(prompt):
            sys.exit("Aborting.")

    def validate_value(self, helper_function, *args):
        """Ask the user whether to ignore a ValueError.

        Args:
          helper_function (function): Validation function to call, which
            may raise a ValueError.
          *args: Arguments to pass to `helper_function`.
        Raises:
          ValueError: if `helper_function` raises a ValueError and the
            user declines to ignore it.
        """
        try:
            helper_function(*args)
        except ValueError as err:
            if not self.confirm("Warning:\n{0}\nContinue anyway?".format(err)):
                raise

    def choose_from_list(self, footer, option_list, default_value,
                         header="", info_list=None):
        """Prompt the user to choose from a list.

        Args:
          footer (str): Prompt string to display following the list
          option_list (list): List of strings to choose amongst
          default_value (str): Default value to select if user declines
          header (str): String to display prior to the list
          info_list (list): Verbose strings to display in place of
              :attr:`option_list`

        Returns:
          str: :attr:`default_value` or an item from :attr:`option_list`.
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

        Args:
          prompt (str): Message to prompt the user with
          default_value (str): Default value to input if the user simply
              hits Enter without entering a value, or if :attr:`force`.

        Returns:
          str: Input value
        """
        if self.force:
            logger.warning("Automatically entering %s in response to '%s'",
                           default_value, prompt)
            return default_value
        return default_value

    def get_password(self, username, host):
        """Get password string from the user.

        Args:
          username (str): Username the password is associated with
          host (str): Host the password is associated with
        Raises:
          NotImplementedError: Must be implemented by a subclass.
        """
        raise NotImplementedError("No implementation of get_password()")


if __name__ == "__main__":   # pragma: no cover
    import doctest
    doctest.testmod()
