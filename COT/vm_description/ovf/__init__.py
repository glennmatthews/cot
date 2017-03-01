# June 2016, Glenn F. Matthews
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

"""Package for handling OVF and OVA virtual machine description files.

The :class:`OVF` class provides an implementation of the
:class:`COT.vm_description.VMDescription` interface. In general, COT
submodules should be agnostic of the internals of this package and should
only use the ``VMDescription`` interface.

API
---

.. autosummary::
  :nosignatures:

  OVF

Exceptions
----------

.. autosummary::
  :nosignatures:

  ~COT.vm_description.ovf.hardware.OVFHardwareDataError
  ~COT.vm_description.ovf.item.OVFItemDataError

Modules
-------

.. autosummary::
  :toctree:

  COT.vm_description.ovf.hardware
  COT.vm_description.ovf.item
  COT.vm_description.ovf.name_helper
  COT.vm_description.ovf.utilities
"""

from .ovf import OVF

__all__ = ('OVF', )
