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

The :class:`~COT.platforms.generic.GenericPlatform` class describes the API
and provides a generic implementation that can be overridden by subclasses
to provide platform-specific logic.

In general, other modules should not instantiate subclasses directly but should
instead use the :func:`~COT.platforms.platform_from_product_class` API to
derive the appropriate subclass instance.

API
---

.. autosummary::
  :nosignatures:

  is_known_product_class
  platform_from_product_class

Platform modules
----------------

.. autosummary::
  :toctree:

  COT.platforms.generic
  COT.platforms.cisco_csr1000v
  COT.platforms.cisco_iosv
  COT.platforms.cisco_iosxrv
  COT.platforms.cisco_iosxrv_9000
  COT.platforms.cisco_nexus_9000v
  COT.platforms.cisco_nxosv
"""

import logging

from .generic import GenericPlatform
from .cisco_csr1000v import CSR1000V
from .cisco_iosv import IOSv
from .cisco_iosxrv import IOSXRv, IOSXRvRP, IOSXRvLC
from .cisco_iosxrv_9000 import IOSXRv9000
from .cisco_nexus_9000v import Nexus9000v
from .cisco_nxosv import NXOSv

logger = logging.getLogger(__name__)


PRODUCT_PLATFORM_MAP = {
    'com.cisco.csr1000v':    CSR1000V,
    'com.cisco.iosv':        IOSv,
    'com.cisco.n9k':         Nexus9000v,
    'com.cisco.nx-osv':      NXOSv,
    'com.cisco.ios-xrv':     IOSXRv,
    'com.cisco.ios-xrv.rp':  IOSXRvRP,
    'com.cisco.ios-xrv.lc':  IOSXRvLC,
    'com.cisco.ios-xrv9000': IOSXRv9000,
    # Some early releases of IOS XRv 9000 used the
    # incorrect string 'com.cisco.ios-xrv64'.
    'com.cisco.ios-xrv64':   IOSXRv9000,
}
"""Mapping of known product class strings to Platform classes."""


def is_known_product_class(product_class):
    """Determine if the given product class string is a known one.

    Args:
      product_class (str): String such as 'com.cisco.iosv'

    Returns:
      bool: Whether product_class is known.

    Examples:
      ::

        >>> is_known_product_class("com.cisco.n9k")
        True
        >>> is_known_product_class("foobar")
        False
    """
    return product_class in PRODUCT_PLATFORM_MAP


def platform_from_product_class(product_class):
    """Get the class of Platform corresponding to a product class string.

    Args:
      product_class (str): String such as 'com.cisco.iosv'

    Returns:
      class: GenericPlatform or a subclass of it

    Examples:
      ::

        >>> platform_from_product_class("com.cisco.n9k")
        <class 'COT.platforms.cisco_nexus_9000v.Nexus9000v'>
        >>> platform_from_product_class(None)
        <class 'COT.platforms.generic.GenericPlatform'>
        >>> platform_from_product_class("frobozz")
        <class 'COT.platforms.generic.GenericPlatform'>
    """
    if product_class is None:
        return GenericPlatform
    if is_known_product_class(product_class):
        return PRODUCT_PLATFORM_MAP[product_class]
    logger.warning("Unrecognized product class '%s' - known classes "
                   "are %s. Treating as a generic platform",
                   product_class, PRODUCT_PLATFORM_MAP.keys())
    return GenericPlatform


__all__ = (
    'is_known_product_class',
    'platform_from_product_class',
)
