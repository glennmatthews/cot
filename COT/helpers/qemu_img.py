#!/usr/bin/env python
#
# qemu_img.py - Helper for 'qemu-img'
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

"""Give COT access to ``qemu-img`` for manipulating disk image formats.

http://www.qemu.org
"""

from .helper import Helper


class QEMUImg(Helper):
    """Helper provider for ``qemu-img`` (http://www.qemu.org)."""

    _provider_package = {
        'apt-get': 'qemu-utils',
        'brew': 'qemu',
        'port': 'qemu',
        'yum': 'qemu-img',
    }

    def __init__(self):
        """Initializer."""
        super(QEMUImg, self).__init__(
            "qemu-img",
            info_uri="http://www.qemu.org",
            version_regexp="qemu-img version ([0-9.]+)")

    def call(self, args, **kwargs):
        """Call qemu-img with the given arguments.

        Caches the output of ``qemu-img info FILE`` commands to save time.

        For the parameters, see :meth:`COT.helpers.helper.Helper.call` etc.
        """
        output = super(QEMUImg, self).call(args, **kwargs)
        if output and args[0] == "info":
            self.cached_output[tuple(args)] = output
        return output
