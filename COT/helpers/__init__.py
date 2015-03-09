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

In general, COT submodules should work through the APIs provided in
:mod:`COT.helpers.api` rather than accessing individual helper program classes.
This gives us the flexibility to change the specific set of helper programs
that are used to provide any given functionality with minimal impact to COT
as a whole.

API
---

.. autosummary::
  :nosignatures:

  ~COT.helpers.api.convert_disk_image
  ~COT.helpers.api.create_disk_image
  ~COT.helpers.api.get_checksum
  ~COT.helpers.api.get_disk_capacity
  ~COT.helpers.api.get_disk_format

Exceptions
----------

.. autosummary::

  ~COT.helpers.helper.HelperError
  ~COT.helpers.helper.HelperNotFoundError

Helper modules
--------------

.. autosummary::
  :toctree:

  COT.helpers.api
  COT.helpers.helper
  COT.helpers.fatdisk
  COT.helpers.mkisofs
  COT.helpers.ovftool
  COT.helpers.qemu_img
  COT.helpers.vmdktool
"""

from .api import convert_disk_image, create_disk_image
from .api import get_checksum, get_disk_capacity, get_disk_format
from .helper import HelperError, HelperNotFoundError

__all__ = ('HelperError', 'HelperNotFoundError',
           'convert_disk_image', 'create_disk_image',
           'get_checksum', 'get_disk_capacity', 'get_disk_format')
