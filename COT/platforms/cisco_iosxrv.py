# September 2016, Glenn F. Matthews
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

"""Platform logic for the Cisco IOS XRv virtual router and its variants.

**Classes**

.. autosummary::
   :nosignatures:

   IOSXRv
   IOSXRvLC
   IOSXRvRP
"""

import logging

from COT.platforms.platform import Platform, Hardware
from COT.data_validation import ValidRange

logger = logging.getLogger(__name__)


class IOSXRv(Platform):
    """Platform-specific logic for Cisco IOS XRv platform."""

    PLATFORM_NAME = "Cisco IOS XRv"

    CONFIG_TEXT_FILE = 'iosxr_config.txt'
    SECONDARY_CONFIG_TEXT_FILE = 'iosxr_config_admin.txt'
    LITERAL_CLI_STRING = None
    SUPPORTED_NIC_TYPES = ["E1000", "virtio"]

    HARDWARE_LIMITS = Platform.HARDWARE_LIMITS.copy()
    HARDWARE_LIMITS.update({
        Hardware.cpus: ValidRange(1, 8),
        Hardware.memory: ValidRange(3072, 8192),
        Hardware.nic_count: ValidRange(1, None),
        Hardware.serial_count: ValidRange(1, 4),
    })

    def guess_nic_name(self, nic_number):
        """MgmtEth0/0/CPU0/0, GigabitEthernet0/0/0/0, Gig0/0/0/1, etc.

        Args:
          nic_number (int): Nth NIC to name.

        Returns:
          * "MgmtEth0/0/CPU0/0"
          * "GigabitEthernet0/0/0/0"
          * "GigabitEthernet0/0/0/1"
          * etc.
        """
        if nic_number == 1:
            return "MgmtEth0/0/CPU0/0"
        else:
            return "GigabitEthernet0/0/0/" + str(nic_number - 2)


class IOSXRvRP(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv HA-capable RP."""

    PLATFORM_NAME = "Cisco IOS XRv route processor card"

    HARDWARE_LIMITS = IOSXRv.HARDWARE_LIMITS.copy()
    HARDWARE_LIMITS.update({
        Hardware.nic_count: ValidRange(1, 2),
    })

    def guess_nic_name(self, nic_number):
        """Fabric and management only.

        Args:
          nic_number (int): Nth NIC to name.

        Returns:
          str: "fabric" or "MgmtEth0/{SLOT}/CPU0/0" only
        """
        if nic_number == 1:
            return "fabric"
        else:
            return "MgmtEth0/{SLOT}/CPU0/" + str(nic_number - 2)


class IOSXRvLC(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv line card."""

    PLATFORM_NAME = "Cisco IOS XRv line card"

    # No bootstrap config for LCs - they inherit from the RP
    CONFIG_TEXT_FILE = None
    SECONDARY_CONFIG_TEXT_FILE = None

    HARDWARE_LIMITS = IOSXRv.HARDWARE_LIMITS.copy()
    HARDWARE_LIMITS.update({
        Hardware.serial_count: ValidRange(0, 4),
    })

    def guess_nic_name(self, nic_number):
        """Fabric interface plus slot-appropriate GigabitEthernet interfaces.

        Args:
            nic_number (int): Nth NIC to name.

        Returns:
            str:
                * "fabric"
                * "GigabitEthernet0/{SLOT}/0/0"
                * "GigabitEthernet0/{SLOT}/0/1"
                * etc.
        """
        if nic_number == 1:
            return "fabric"
        else:
            return "GigabitEthernet0/{SLOT}/0/" + str(nic_number - 2)


Platform.PRODUCT_PLATFORM_MAP['com.cisco.ios-xrv'] = IOSXRv
Platform.PRODUCT_PLATFORM_MAP['com.cisco.ios-xrv.rp'] = IOSXRvRP
Platform.PRODUCT_PLATFORM_MAP['com.cisco.ios-xrv.lc'] = IOSXRvLC
