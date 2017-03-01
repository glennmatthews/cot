#!/usr/bin/env python
#
# command.py - Abstract interface for COT command implementations.
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

"""Parent classes for implementing COT subcommands.

**Classes**

.. autosummary::
  :nosignatures:

  Command
  ReadCommand
  ReadWriteCommand
"""

import os.path
import logging

from COT.data_validation import InvalidInputError
from COT.vm_description import VMDescription

logger = logging.getLogger(__name__)

command_classes = []
"""List of concrete command classes"""


class Command(object):
    """Abstract interface for COT commands.

    Attributes:
    :attr:`vm`,
    :attr:`ui`

    .. note :: Generally a command should not inherit directly from this class,
      but should instead subclass :class:`ReadCommand` or
      :class:`ReadWriteCommand` as appropriate.
    """

    def __init__(self, ui):
        """Instantiate this command with the given UI.

        Args:
          ui (UI): User interface instance.
        """
        self.vm = None
        """Virtual machine description (:class:`VMDescription`)."""
        self.ui = ui
        """User interface instance (:class:`~ui_shared.UI` or subclass)."""

    def ready_to_run(self):  # pylint: disable=no-self-use
        """Check whether the module is ready to :meth:`run`.

        Returns:
          tuple: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        return True, "Ready to go!"

    def run(self):
        """Do the actual work of this command.

        Raises:
          InvalidInputError: if :meth:`ready_to_run` reports ``False``
        """
        (ready, reason) = self.ready_to_run()
        if not ready:
            raise InvalidInputError(reason)
        # Do the work now...

    def finished(self):
        """Do any final actions before being destroyed.

        This class does nothing; subclasses may choose to do things like
        write their VM state out to a file.
        """
        pass

    def destroy(self):
        """Destroy any VM associated with this command."""
        if self.vm is not None:
            self.vm.destroy()
            self.vm = None

    def create_subparser(self):
        """Add subparser for the CLI of this command."""
        pass


class ReadCommand(Command):
    """Command that reads from but does not write to the OVF, such as 'deploy'.

    Inherited attributes:
    :attr:`vm`,
    :attr:`ui`

    Attributes:
    :attr:`package`
    """

    def __init__(self, ui):
        """Instantiate this command with the given UI.

        Args:
          ui (UI): User interface instance.
        """
        super(ReadCommand, self).__init__(ui)
        self._package = None

    @property
    def package(self):
        """VM description file to read from.

        Calls :meth:`COT.vm_description.VMDescription.factory` to instantiate
        :attr:`self.vm` from the provided file.

        Raises:
          InvalidInputError: if the file does not exist.
        """
        return self._package

    @package.setter
    def package(self, value):
        if value is not None and not os.path.exists(value):
            raise InvalidInputError("Specified package {0} does not exist!"
                                    .format(value))
        if self.vm is not None:
            self.vm.destroy()
            self.vm = None
        if value is not None:
            self.vm = VMDescription.factory(value, None)
        self._package = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        Returns:
          tuple: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.package is None:
            return False, "PACKAGE is a mandatory argument!"
        return super(ReadCommand, self).ready_to_run()


class ReadWriteCommand(Command):
    """Command that reads from and writes to a VM description.

    Inherited attributes:
    :attr:`vm`,
    :attr:`ui`

    Attributes:
    :attr:`package`,
    :attr:`output`
    """

    def __init__(self, ui):
        """Instantiate this command with the given UI.

        Args:
          ui (UI): User interface instance.
        """
        super(ReadWriteCommand, self).__init__(ui)
        self._package = None
        # Default to an unspecified output rather than no output
        self._output = ""

    @property
    def package(self):
        """VM description file to read (and possibly write).

        Calls :meth:`COT.vm_description.VMDescription.factory` to instantiate
        :attr:`self.vm` from the provided file.

        Raises:
          InvalidInputError: if the file does not exist.
        """
        return self._package

    @package.setter
    def package(self, value):
        if value is not None and not os.path.exists(value):
            raise InvalidInputError("Specified package {0} does not exist!"
                                    .format(value))
        if self.vm is not None:
            self.vm.destroy()
            self.vm = None
        if value is not None:
            self.vm = VMDescription.factory(value, self.output)
        self._package = value

    @property
    def output(self):
        """Output file for this command.

        If the specified file already exists,  will prompt the user
        (:meth:`~COT.ui_shared.UI.confirm_or_die`) to
        confirm overwriting the existing file.
        """
        return self._output

    @output.setter
    def output(self, value):
        if value and value != self._output and os.path.exists(value):
            self.ui.confirm_or_die("Overwrite existing file {0}?"
                                   .format(value))
        self._output = value
        if self.vm is not None:
            self.vm.output_file = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        Returns:
          tuple: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.package is None:
            return False, "PACKAGE is a mandatory argument!"
        return super(ReadWriteCommand, self).ready_to_run()

    def run(self):
        """Do the actual work of this command.

        If :attr:`output` was not previously set, automatically
        sets it to the value of :attr:`PACKAGE`.

        Raises:
          InvalidInputError: if :meth:`ready_to_run` reports ``False``
        """
        super(ReadWriteCommand, self).run()

        if not self.output:
            self.output = self.package
        # Do the work now...

    def finished(self):
        """Write the current VM state out to disk if requested."""
        # do any command-specific work here, then:
        if self.vm is not None:
            self.vm.write()
        super(ReadWriteCommand, self).finished()
