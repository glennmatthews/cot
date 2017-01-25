#!/usr/bin/env python
#
# mkisofs.py - Helper for 'mkisofs' and 'genisoimage'
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

"""Give COT access to mkisofs, genisoimage, or xorriso for creating ISO images.

http://cdrecord.org/
https://www.gnu.org/software/xorriso/

**Classes**

.. autosummary::
  :nosignatures:

  MkISOFS
  GenISOImage
  XorrISO
"""

from .helper import Helper


class MkISOFS(Helper):
    """Helper provider for ``mkisofs``.

    http://cdrecord.org/
    """

    _provider_package = {
        'brew': 'cdrtools',
        'port': 'cdrtools',
    }

    def __init__(self):
        """Initializer."""
        super(MkISOFS, self).__init__("mkisofs",
                                      version_regexp="mkisofs ([0-9.]+)")


class GenISOImage(Helper):
    """Helper provider for ``genisoimage``, a fork of mkisofs."""

    _provider_package = {
        'apt-get': 'genisoimage',
        'yum': 'genisoimage',
    }

    def __init__(self):
        """Initializer."""
        super(GenISOImage, self).__init__(
            "genisoimage",
            version_regexp="genisoimage ([0-9.]+)")


class XorrISO(Helper):
    """Helper provider for ``xorriso``.

    https://www.gnu.org/software/xorriso/
    """

    _provider_package = {
        'apt-get': 'xorriso',
    }

    def __init__(self):
        """Initializer."""
        super(XorrISO, self).__init__(
            "xorriso",
            version_regexp="xorriso ([0-9.]+)")
