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
from COT.utilities import available_bytes_at_path, pretty_bytes

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
        """User interface instance (:class:`~COT.ui.UI` or subclass)."""

    def ready_to_run(self):  # pylint: disable=no-self-use
        """Check whether the module is ready to :meth:`run`.

        Returns:
          tuple: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.vm and not self.check_disk_space(
                self.working_dir_disk_space_required(),
                self.vm.working_dir, "Temporary storage"):
            return (False,
                    "Insufficient disk space available for temporary file"
                    " storage in working directory {0}."
                    "\nTo change working directory location, set $TMPDIR"
                    " in your environment before calling COT."
                    .format(self.vm.working_dir))

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

    def working_dir_disk_space_required(self):
        """How much space this module will require in :attr:`working_dir`.

        By default, assumes the entire VM may be written to working directory.
        Subclasses may wish to extend or override this.

        Returns:
          int: Predicted temporary storage requirements.
        """
        if self.vm is not None:
            return self.vm.predicted_output_size()
        return 0

    def check_disk_space(self, required_size, location,
                         label="File", die=False):
        """Check whether there is sufficient disk space available.

        If there is insufficient space, warn the user before continuing.

        Args:
          required_size (int): Bytes required
          location (str): Path to check availability of.
          label (str): Descriptive label to display in user messages.
          die (bool): If True, use :meth:`~COT.ui.UI.confirm_or_die` instead
            of :meth:`~COT.ui.UI.confirm`

        Returns:
          bool: Whether sufficient space is available (or if not,
            whether the user has opted to continue anyway).
        """
        dir_path = os.path.abspath(location)
        while dir_path and not os.path.isdir(dir_path):
            dir_path = os.path.dirname(dir_path)
        # The above will never fail to find something - in the worst case,
        # it may ascend all the way to the filesystem root, but stop there.

        available = available_bytes_at_path(dir_path)
        logger.verbose("Checking requested disk space %s against available"
                       " space in %s (%s)", pretty_bytes(required_size),
                       dir_path, pretty_bytes(available))
        if required_size <= available:
            return True
        msg = ("{0} requires {1} of disk space but only {2} is available"
               " at {3}. Operation may fail. Continue anyway?"
               .format(label, pretty_bytes(required_size),
                       pretty_bytes(available), location))
        if die:
            self.ui.confirm_or_die(msg)
            return True
        else:
            return self.ui.confirm(msg)


class ReadCommand(Command):
    """Command, such as 'deploy', that reads from a VM file to create its vm.

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


class ReadWriteCommand(ReadCommand):
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
        # Default to an unspecified output rather than no output
        self._output = ""
        self._predicted_output_size = 0

    # Overriding a parent class's property is a bit ugly in Python.
    @ReadCommand.package.setter
    def package(self, value):
        if value is not None and not os.path.exists(value):
            raise InvalidInputError("Specified package {0} does not exist!"
                                    .format(value))
        if self.vm is not None:
            self.vm.destroy()
            self.vm = None
        if value is not None:
            # Unlike ReadCommand, we pass self.output to the VM factory
            self.vm = VMDescription.factory(value, self.output)
            # And we also check whether output space will be an issue
            self._check_and_warn_disk_space()
        self._package = value

    @property
    def output(self):
        """Output file for this command.

        If the specified file already exists,  will prompt the user
        (:meth:`~COT.ui.UI.confirm_or_die`) to
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
            self._check_and_warn_disk_space(force_prompt=True)

    def _check_and_warn_disk_space(self, force_prompt=False):
        """Check estimated disk space required against the available space.

        If the estimate exceeds the available, warn the user and prompt
        for confirmation to continue anyway or else abort.

        Safe to call repeatedly - will only prompt the user again if the
        space estimate changes or if ``force_prompt`` is True.

        Args:
          force_prompt (bool): If True, reprompt the user even if the estimate
           has not changed.

        Raises:
          SystemExit: if disk space is insufficient and the user declines
            to continue regardless of this information.
        """
        if not self.vm:
            logger.debug("Input VM not yet set, so not yet able "
                         " to check estimated output size.")
            return
        if not self.output:
            logger.debug("Output location not yet set, so not yet able"
                         " to check disk space")
            return

        predicted = self.vm.predicted_output_size()
        if predicted == self._predicted_output_size and not force_prompt:
            return

        if predicted != self._predicted_output_size:
            logger.verbose("Predicted disk usage changed from %s to %s",
                           pretty_bytes(self._predicted_output_size),
                           pretty_bytes(predicted))
            self._predicted_output_size = predicted

        # Compare double predicted size against available space to provide
        # sufficient margin of error against temporary files, other processes
        # consuming disk space, etc.
        self.check_disk_space(2 * predicted, self.output, "VM output",
                              die=True)

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
            self._check_and_warn_disk_space()
            self.vm.write()
        super(ReadWriteCommand, self).finished()
