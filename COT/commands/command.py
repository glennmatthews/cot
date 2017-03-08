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

command_classes = []   # pylint: disable=invalid-name
"""Dynamically constructed list of concrete command classes."""


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
        self._cached_disk_requirements = {}
        """Private storage for :meth:`check_disk_space`."""

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        Returns:
          tuple: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.vm and not self.check_disk_space(
                self.working_dir_disk_space_required(),
                self.vm.working_dir,
                label="Temporary storage",
                context="You can choose a different location by setting"
                " $TMPDIR in your environment before calling COT"):
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
                         label="File", context=None,
                         force_check=False, die=False):
        """Check if there is sufficient disk space available at a location.

        If there is insufficient space, warn the user before continuing.

        Caches space requirements per location, so it's safe to call
        repeatedly, as it will only re-check (and possibly re-prompt the user)
        if:

          1. a different location is requested
          2. or the required size changes
          3. or ``force_check`` is True.

        Args:
          required_size (int): Bytes required
          location (str): Path to check availability of.
          label (str): Descriptive label to display in user messages.
          context (str): Optional string for additional context to provide
            when prompting the user.
          force_check (bool): If True, re-check and re-prompt the user even
            if this location has previously been checked and its
            ``required_size`` has not changed.
          die (bool): If True, use :meth:`~COT.ui.UI.confirm_or_die` instead
            of :meth:`~COT.ui.UI.confirm`

        Returns:
          bool: Whether sufficient space is available (or if not,
            whether the user has opted to continue anyway).

        Raises:
          SystemExit: if disk space is insufficient and ``die`` is True and
            the user declines to continue.
        """
        dir_path = os.path.abspath(location)
        while dir_path and not os.path.isdir(dir_path):
            dir_path = os.path.dirname(dir_path)
        # The above will never fail to find something - in the worst case,
        # it may ascend all the way to the filesystem root, but stop there.

        if dir_path in self._cached_disk_requirements and not force_check:
            prev_req, prev_avail = self._cached_disk_requirements[dir_path]
            if required_size <= prev_req:
                return required_size <= prev_avail

        logger.verbose("Checking requested disk space (%s) against"
                       " available space in %s", pretty_bytes(required_size),
                       dir_path)

        available = available_bytes_at_path(dir_path)
        self._cached_disk_requirements[dir_path] = (required_size, available)

        if required_size <= available:
            return True

        msg = ("{0} may require approximately {1} of disk space,"
               " but only {2} is available at {3}."
               .format(label, pretty_bytes(required_size),
                       pretty_bytes(available), location))
        if context:
            msg += "\n({0})".format(context)
        msg += "\nOperation may fail. Continue anyway?"
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

    # Overriding a parent class's property is a bit ugly in Python.
    # Also, Pylint bug: https://github.com/PyCQA/pylint/issues/844
    @ReadCommand.package.setter   # pylint: disable=no-member
    def package(self,   # pylint: disable=missing-type-doc,missing-param-doc
                value):
        """VM description file to read (and write to unless ``output`` is set).

        Calls :meth:`COT.vm_description.VMDescription.factory` to instantiate
        :attr:`self.vm` from the provided file.

        Raises:
          InvalidInputError: if the file does not exist.
          SystemExit: if available disk space versus predicted amount required
            for output is insufficient, and the user declines to continue
            in response to this information.
        """
        if value is not None and not os.path.exists(value):
            raise InvalidInputError("Specified package {0} does not exist!"
                                    .format(value))
        if self.vm is not None:
            self.vm.destroy()
            self.vm = None
        if value is not None:
            # Unlike ReadCommand, we pass self.output to the VM factory
            self.vm = VMDescription.factory(value, self.output)
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
        if value:
            value = os.path.abspath(value)

        if value == self._output:
            return

        if value:
            if os.path.exists(value):
                if not os.path.isfile(value):
                    raise InvalidInputError(
                        "Output location '{0}' exists but is not a normal file"
                        .format(value))
                self.ui.confirm_or_die("Overwrite existing file {0}?"
                                       .format(value))
            else:
                # Make sure the containing directory at least exists
                dirpath = os.path.dirname(value)
                if not os.path.exists(dirpath):
                    raise InvalidInputError(
                        "Output parent path '{0}/' does not exist"
                        .format(dirpath))
                elif not os.path.isdir(dirpath):
                    raise InvalidInputError(
                        "Output parent path '{0}/' is not a directory"
                        .format(dirpath))

        self._output = value
        if self.vm is not None:
            self.vm.output_file = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        Returns:
          tuple: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        ready, reason = super(ReadWriteCommand, self).ready_to_run()
        if ready:
            output_loc = self.output
            if not output_loc:
                output_loc = self.package
            if not self.check_disk_space(2 * self.vm.predicted_output_size(),
                                         output_loc,
                                         label="VM output"):
                return (False,
                        "Insufficient disk space available to guarantee"
                        " successful output to {0}. You may wish to specify"
                        " a different location using the --output option."
                        .format(output_loc))
        return (ready, reason)

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
            # One more sanity check
            self.check_disk_space(2 * self.vm.predicted_output_size(),
                                  self.output, label="VM output", die=True)
            self.vm.write()
        super(ReadWriteCommand, self).finished()
