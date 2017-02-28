# February 2017, Glenn F. Matthews
# Copyright (c) 2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Support for various virtual machine description formats (OVF, OVA, etc.).

The :class:`~COT.vm_description.VMDescription` class describes the abstract
API that is implemented by various subclasses.

In general, other modules should not access subclasses directly but should
instead use the :meth:`~COT.vm_description.VMDescription.factory`
API to derive the appropriate subclass object.

API
---

.. autosummary::
  :nosignatures:

  VMDescription
  VMInitError

VM description modules
-------------------------

.. autosummary::
  :toctree:

  COT.vm_description.ovf
"""

import logging

# flake8: noqa: F401

from .vm_description import VMDescription, VMInitError
from .ovf import OVF

logger = logging.getLogger(__name__)


__all__ = (
    'VMDescription',
    'VMInitError',
)
