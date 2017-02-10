#!/usr/bin/env python
#
# brew.py - Wrapper for the Homebrew 'brew' package manager.
#
# January 2017, Glenn F. Matthews
# Copyright (c) 2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Wrapper for the Homebrew 'brew' package manager for Mac (http://brew.sh)."""

import logging

from COT.helpers.helper import PackageManager

logger = logging.getLogger(__name__)


class Brew(PackageManager):
    """The 'brew' package manager utility."""

    def __init__(self):
        """Initializer."""
        super(Brew, self).__init__(
            "brew",
            info_uri="http://brew.sh/",
            version_args=['--version'],
            version_regexp=r"Homebrew ([0-9.]+)")

    def install_package(self, package):
        """Install the requested package if needed.

        Args:
          package (str): Name of the package to install, or a list of
            parameters used to install the package.
        """
        # Brew automatically updates when called so no need for us to do it.
        if isinstance(package, list):
            cmd = ['install'] + package
        else:
            cmd = ['install', package]
        self.call(cmd, capture_output=False)
