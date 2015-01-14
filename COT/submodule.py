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

class COTSubmodule(object):
    """Abstract interface for COT command submodules."""

    def __init__(self, UI, arg_names):
        self.args = {}
        for name in arg_names:
            self.args[name] = None
        self.vm = None
        self.UI = UI


    def validate_arg(self, arg, value):
        """Check whether it's OK to set the given argument to the given value.
        Returns either (True, massaged_value) or (False, reason)"""
        if not arg in self.args.keys():
            return False, "unrecognized argument '{0}'".format(arg)
        # Generic input validation common across all submodules
        if arg == "PACKAGE":
            if not os.path.exists(value):
                return False, ("Specified package {0} does not exist!"
                               .format(value))
        elif arg == "output":
            if (value is not None and value != self.get_value(arg) and
                os.path.exists(value)):
                self.UI.confirm_or_die("Overwrite existing file {0}?"
                                       .format(value))

        return True, value


    def set_value(self, arg, value):
        """Set the given argument to the given value"""
        if not arg in self.args.keys():
            return
        valid, value_or_reason = self.validate_arg(arg, value)
        if not valid:
            raise InvalidInputError(value_or_reason)
        else:
            value = value_or_reason
        self.args[arg] = value
        # Generic operations
        if arg == "PACKAGE":
            self.vm = VMFactory.create(value, self.get_value("output"))
        elif arg == "output":
            if self.vm is not None:
                self.vm.set_output_file(value)


    def get_value(self, arg):
        """Get the current value of the given arg"""
        value = self.args.get(arg, None)

        return value


    def ready_to_run(self):
        """Are we ready to go?
        Returns the tuple (ready, reason)"""
        # do any subclass-specific work here, then call super()

        if "PACKAGE" in self.args.keys() and not self.get_value("PACKAGE"):
            return False, "PACKAGE is a mandatory argument!"

        return True, "Ready to go!"


    def run(self):
        (ready, reason) = self.ready_to_run()
        if not ready:
            raise InvalidInputError(reason)

        if "output" in self.args.keys() and "PACKAGE" in self.args.keys():
            output = self.get_value("output")
            if not output:
                self.set_value("output", self.get_value("PACKAGE"))

        # do the work now...

    def finished(self):
        # do any submodule-specific work here, then:
        if self.vm is not None:
            self.vm.write()


    def create_subparser(self, parent):
        """Add subparser under the given parent parser, representing the CLI.
        Returns (label, subparser)"""
        return "", None
