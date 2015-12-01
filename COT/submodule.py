#!/usr/bin/env python
#
# submodule.py - Abstract interface for COT 'command' submodules.
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

"""Parent classes for implementing COT subcommands.

**Classes**

.. autosummary::
  :nosignatures:

  COTGenericSubmodule
  COTReadOnlySubmodule
  COTSubmodule
"""

import os.path
import logging

from .data_validation import InvalidInputError
from .vm_factory import VMFactory

logger = logging.getLogger(__name__)


class COTGenericSubmodule(object):
    """Abstract interface for COT command submodules.

    Attributes:
    :attr:`vm`,
    :attr:`UI`

    .. note :: Generally a command should not inherit directly from this class,
      but should instead subclass :class:`COTReadOnlySubmodule` or
      :class:`COTSubmodule` as appropriate.
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        self.vm = None
        """Virtual machine description (:class:`VMDescription`)."""
        self.UI = UI
        """User interface instance (:class:`~ui_shared.UI` or subclass)."""

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        return True, "Ready to go!"

    def run(self):
        """Do the actual work of this submodule.

        :raises: :exc:`.InvalidInputError` if :meth:`ready_to_run`
          reports ``False``
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
        """Destroy any VM associated with this submodule."""
        if self.vm is not None:
            self.vm.destroy()
            self.vm = None

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        :param object parent: Subparser grouping object returned by
            :meth:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
        pass


class COTReadOnlySubmodule(COTGenericSubmodule):
    """Class for submodules that do not modify the OVF, such as 'deploy'.

    Inherited attributes:
    :attr:`vm`,
    :attr:`UI`

    Attributes:
    :attr:`package`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTReadOnlySubmodule, self).__init__(UI)
        self._package = None

    @property
    def package(self):
        """VM description file to read from.

        Calls :meth:`COT.vm_factory.VMFactory.create` to instantiate
        :attr:`self.vm` from the provided file.

        :raises: :exc:`.InvalidInputError` if the file does not exist.
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
            self.vm = VMFactory.create(value, None)
        self._package = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.package is None:
            return False, "PACKAGE is a mandatory argument!"
        return super(COTReadOnlySubmodule, self).ready_to_run()


class COTSubmodule(COTGenericSubmodule):
    """Class for submodules that read and write the OVF.

    Inherited attributes:
    :attr:`vm`,
    :attr:`UI`

    Attributes:
    :attr:`package`,
    :attr:`output`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTSubmodule, self).__init__(UI)
        self._package = None
        # Default to an unspecified output rather than no output
        self._output = ""

    @property
    def package(self):
        """VM description file to read (and possibly write).

        Calls :meth:`COT.vm_factory.VMFactory.create` to instantiate
        :attr:`self.vm` from the provided file.

        :raises: :exc:`.InvalidInputError` if the file does not exist.
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
            self.vm = VMFactory.create(value, self.output)
        self._package = value

    @property
    def output(self):
        """Output file for this submodule.

        If the specified file already exists,  will prompt the user
        (:meth:`~COT.ui_shared.UI.confirm_or_die`) to
        confirm overwriting the existing file.
        """
        return self._output

    @output.setter
    def output(self, value):
        if value and value != self._output and os.path.exists(value):
            self.UI.confirm_or_die("Overwrite existing file {0}?"
                                   .format(value))
        self._output = value
        if self.vm is not None:
            self.vm.output_file = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.package is None:
            return False, "PACKAGE is a mandatory argument!"
        return super(COTSubmodule, self).ready_to_run()

    def run(self):
        """Do the actual work of this submodule.

        If :attr:`output` was not previously set, automatically
        sets it to the value of :attr:`PACKAGE`.

        :raises: :exc:`.InvalidInputError` if :meth:`ready_to_run`
          reports ``False``
        """
        super(COTSubmodule, self).run()

        if not self.output:
            self.output = self.package
        # Do the work now...

    def finished(self):
        """Write the current VM state out to disk if requested."""
        # do any submodule-specific work here, then:
        if self.vm is not None:
            self.vm.write()
        super(COTSubmodule, self).finished()
