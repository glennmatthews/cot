# October 2013, Glenn F. Matthews
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

"""Package for identifying guest platforms and handling platform differences.

The :class:`~COT.platforms.platform.Platform` class describes the API
and provides a generic implementation that can be overridden by subclasses
to provide platform-specific logic.

In general, other modules should not access subclasses directly but should
instead use the :meth:`~COT.platforms.platform.Platform.for_product_string`
API to derive the appropriate subclass object.

API
---

.. autosummary::
  :nosignatures:

  ~COT.platforms.platform.Platform

Platform modules
----------------

.. autosummary::
  :toctree:

  COT.platforms.platform
  COT.platforms.cisco_csr1000v
  COT.platforms.cisco_iosv
  COT.platforms.cisco_iosxrv
  COT.platforms.cisco_iosxrv_9000
  COT.platforms.cisco_nexus_9000v
  COT.platforms.cisco_nxosv
"""

import logging

# flake8: noqa: F401

from .platform import Platform
from .cisco_csr1000v import CSR1000V
from .cisco_iosv import IOSv
from .cisco_iosxrv import IOSXRv, IOSXRvRP, IOSXRvLC
from .cisco_iosxrv_9000 import IOSXRv9000
from .cisco_nexus_9000v import Nexus9000v
from .cisco_nxosv import NXOSv

logger = logging.getLogger(__name__)


__all__ = (
    'Platform',
)
