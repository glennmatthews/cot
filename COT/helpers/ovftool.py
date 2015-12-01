#!/usr/bin/env python
#
# ovftool.py - Helper for 'ovftool'
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2013-2015 the COT project developers.
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

import logging

from .helper import Helper

logger = logging.getLogger(__name__)


class OVFTool(Helper):
    """Helper provider for ``ovftool`` from VMware.

    https://www.vmware.com/support/developer/ovf/

    **Methods**

    .. autosummary::
      :nosignatures:

      install_helper
      validate_ovf
    """

    def __init__(self):
        """Initializer."""
        super(OVFTool, self).__init__("ovftool",
                                      version_regexp="ovftool ([0-9.]+)")

    def install_helper(self):
        """Install ``ovftool``.

        :raise: :exc:`NotImplementedError` as VMware does not currently provide
          any mechanism for automatic download of ovftool.
        """
        if self.path:
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.name, self.path))
            return
        raise NotImplementedError(
            "No support for automated installation of ovftool, "
            "as VMware requires a site login to download it.\n"
            "See https://www.vmware.com/support/developer/ovf/")

    def validate_ovf(self, ovf_file):
        """Use VMware's ``ovftool`` program to validate an OVF or OVA.

        This checks the file against the OVF standard and any VMware-specific
        requirements.

        :param str ovf_file: File to validate
        :return: Output from ``ovftool``
        :raise HelperNotFoundError: if ``ovftool`` is not found.
        :raise HelperError: if ``ovftool`` regards the file as invalid
        """
        return self.call_helper(['--schemaValidate', ovf_file])
