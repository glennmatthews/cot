# October 2016, Glenn F. Matthews
# Copyright (c) 2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Package for handling various disk file types (VMDK, ISO, QCOW2, etc.).

Tries to provide an API that abstracts away differences in how the
various types need to be operated on (e.g., qemu-img, mkisofs, etc.).

API
---

.. autosummary::
  :nosignatures:

  DiskRepresentation

Disk modules
------------

.. autosummary::
  :toctree:

  COT.disks.iso
  COT.disks.qcow2
  COT.disks.raw
  COT.disks.vmdk
"""

# flake8: noqa: F401

from .disk import DiskRepresentation
from .iso import ISO
from .qcow2 import QCOW2
from .raw import RAW
from .vmdk import VMDK

__all__ = (
    'DiskRepresentation',
)
