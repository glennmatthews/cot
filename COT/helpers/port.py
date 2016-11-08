#!/usr/bin/env python
#
# port.py - Wrapper for the MacPorts 'port' package manager.
#
# October 2016, Glenn F. Matthews
# Copyright (c) 2015-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Wrapper for the MacPorts 'port' package manager."""

import logging

from COT.helpers.helper import PackageManager

logger = logging.getLogger(__name__)


class Port(PackageManager):
    """The 'port' package manager utility."""

    _updated = False

    def __init__(self):
        """Initializer."""
        super(Port, self).__init__(
            "port",
            info_uri="https://www.macports.org/",
            version_args=['version'])

    def install_package(self, package):
        """Install the requested package if needed.

        Args:
          package (str): Name of the package to install.
        """
        # Check for updates
        if not Port._updated:
            self.call(['selfupdate'],
                      capture_output=False, retry_with_sudo=True)
            Port._updated = True
        self.call(['install', package],
                  capture_output=False, retry_with_sudo=True)
