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

import os.path
import logging

from .data_validation import InvalidInputError
from .vm_factory import VMFactory

logger = logging.getLogger(__name__)


class COTGenericSubmodule(object):
    """Abstract interface for COT command submodules."""

    def __init__(self, UI):
        self.vm = None
        self.UI = UI

    def ready_to_run(self):
        """Are we ready to go?

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        return True, "Ready to go!"

    def run(self):
        """Do the actual work of this submodule.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        (ready, reason) = self.ready_to_run()
        if not ready:
            raise InvalidInputError(reason)
        # Do the work now...

    def finished(self):
        pass

    def destroy(self):
        if self.vm is not None:
            self.vm.destroy()
            self.vm = None

    def create_subparser(self, parent):
        """Add subparser for the CLI of this submodule under the given parent
        subparser grouping.

        :param object parent: Subparser grouping object returned by
            :func:`ArgumentParser.add_subparsers`

        :returns: ``(label, subparser)`` or ``("", None)`` if this module has
            no CLI
        """
        return "", None


class COTReadOnlySubmodule(COTGenericSubmodule):
    "Class for submodules that do not modify the OVF, such as 'deploy'"

    def __init__(self, UI):
        super(COTReadOnlySubmodule, self).__init__(UI)
        self._package = None

    @property
    def package(self):
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
        if self.package is None:
            return False, "PACKAGE is a mandatory argument!"
        return super(COTReadOnlySubmodule, self).ready_to_run()


class COTSubmodule(COTGenericSubmodule):
    "Class for submodules that read and write the OVF"

    def __init__(self, UI):
        super(COTSubmodule, self).__init__(UI)
        self._package = None
        # Default to an unspecified output rather than no output
        self._output = ""

    @property
    def package(self):
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
        return self._output

    @output.setter
    def output(self, value):
        if value and value != self._output and os.path.exists(value):
            self.UI.confirm_or_die("Overwrite existing file {0}?"
                                   .format(value))
        self._output = value
        if self.vm is not None:
            self.vm.set_output_file(value)

    def ready_to_run(self):
        if self.package is None:
            return False, "PACKAGE is a mandatory argument!"
        return super(COTSubmodule, self).ready_to_run()

    def run(self):
        super(COTSubmodule, self).run()

        if not self.output:
            self.output = self.package
        # Do the work now...

    def finished(self):
        # do any submodule-specific work here, then:
        if self.vm is not None:
            self.vm.write()
        super(COTSubmodule, self).finished()
