#!/usr/bin/env python
#
# ui_shared.py - abstraction between CLI and GUI
#
# December 2014, Glenn F. Matthews
# Copyright (c) 2014 the COT project developers.
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

logger = logging.getLogger(__name__)

class UI(object):
    """Abstract user interface functionality.
    Can also be used in test code as a stub that autoconfirms everything."""

    def __init__(self, force=False):
        self.force = force

    def confirm(self, prompt):
        """Prompts user to confirm the requested operation, or auto-accepts
        if 'force' is set to True."""
        if self.force:
            logger.warning("Automatically agreeing to '{0}'".format(prompt))
            return True
        return True

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
        raise NotImplementedError("don't know how to get password from user")
