#!/usr/bin/env python
#
# ovftool.py - Helper for 'ovftool'
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2013-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Give COT access to ``ovftool`` for validating and deploying OVF to ESXi.

https://www.vmware.com/support/developer/ovf/
"""

from .helper import Helper


class OVFTool(Helper):
    """Helper provider for ``ovftool`` from VMware.

    https://www.vmware.com/support/developer/ovf/
    """

    def __init__(self):
        """Initializer."""
        super(OVFTool, self).__init__(
            "ovftool",
            info_uri="https://www.vmware.com/support/developer/ovf/",
            version_regexp="ovftool ([0-9.]+)")

    @property
    def installable(self):
        """COT can't install ovftool because of VMware site restrictions."""
        return False

    def unsure_how_to_install(self):
        """Return a NotImplementedError about missing install logic.

        We override the default install implementation to raise a more
        detailed error message for ovftool.
        """
        return NotImplementedError(
            "No support for automated installation of ovftool, as VMware "
            "requires a site login to download it. See "
            "https://www.vmware.com/support/developer/ovf/"
        )
