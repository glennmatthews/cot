# February 2015, Glenn F. Matthews
# Copyright (c) 2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""
Provide various non-Python helper programs that COT makes use of.

In general, COT submodules do not access the contents of this package directly
but instead work through the :mod:`COT.helper_tools` module. This gives us the
flexibility to change the specific set of helper programs that are used to
provide any given functionality with minimal impact to COT as a whole.

.. autosummary::
  :toctree:

  COT.helpers.helper
  COT.helpers.fatdisk
  COT.helpers.mkisofs
  COT.helpers.ovftool
  COT.helpers.qemu_img
  COT.helpers.vmdktool
"""

from .helper import Helper, HelperError, HelperNotFoundError
from .fatdisk import FatDisk
from .mkisofs import MkIsoFS
from .ovftool import OVFTool
from .qemu_img import QEMUImg
from .vmdktool import VmdkTool

__all__ = ['Helper', 'HelperError', 'HelperNotFoundError',
           'FatDisk', 'MkIsoFS', 'OVFTool', 'QEMUImg', 'VmdkTool']
