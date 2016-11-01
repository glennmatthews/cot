#!/usr/bin/env python
#
# yum.py - Wrapper for the 'yum' package manager.
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

"""Wrapper for the 'yum' package manager."""

import logging

from COT.helpers.helper import PackageManager

logger = logging.getLogger(__name__)


class Yum(PackageManager):
    """The 'yum' package manager utility."""

    def __init__(self):
        """Initializer."""
        super(Yum, self).__init__("yum")

    def install_package(self, package):
        """Install the requested package if needed.

        Args:
          package (str): Name of the package to install.
        """
        self.call(['--quiet', 'install', package],
                  capture_output=False, retry_with_sudo=True)
