#!/usr/bin/env python
#
# apt_get.py - Wrapper for the 'apt-get' package manager.
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

"""Wrapper for the 'apt-get' package manager."""

import logging
import re

from COT.helpers.helper import PackageManager, helpers

logger = logging.getLogger(__name__)


class AptGet(PackageManager):
    """The 'apt-get' package manager utility."""

    _updated = False

    def __init__(self):
        """Initializer."""
        super(AptGet, self).__init__("apt-get", version_regexp="apt ([0-9.]+)")

    def install_package(self, package):
        """Install the requested package if needed.

        Args:
          package (str): Name of the package to install.
        """
        # Check whether it's already installed
        if re.search(r"install ok installed",
                     helpers['dpkg'].call(['-s', package],
                                          require_success=False)):
            return
        # Update the repository if needed
        if not AptGet._updated:
            self.call(['-q', 'update'],
                      capture_output=False, retry_with_sudo=True)
            AptGet._updated = True
        self.call(['-q', 'install', package],
                  capture_output=False, retry_with_sudo=True)
