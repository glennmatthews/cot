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

"""Platform logic for the Cisco IOS XRv 9000 virtual router."""

import logging

from COT.platforms.platform import Platform, Hardware
from COT.platforms.cisco_iosxrv import IOSXRv
from COT.data_validation import ValidRange

logger = logging.getLogger(__name__)


class IOSXRv9000(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv 9000 platform."""

    PLATFORM_NAME = "Cisco IOS XRv 9000"
    SUPPORTED_NIC_TYPES = ["E1000", "virtio", "VMXNET3"]

    HARDWARE_LIMITS = IOSXRv.HARDWARE_LIMITS.copy()
    HARDWARE_LIMITS.update({
        Hardware.cpus: ValidRange(1, 32),
        Hardware.memory: ValidRange(8192, None),
        Hardware.nic_count: ValidRange(4, None),
    })

    def guess_nic_name(self, nic_number):
        """MgmtEth0/0/CPU0/0, CtrlEth, DevEth, GigabitEthernet0/0/0/0, etc.

        Args:
          nic_number (int): Nth NIC to name.

        Returns:
          * "MgmtEth0/0/CPU0/0"
          * "CtrlEth"
          * "DevEth"
          * "GigabitEthernet0/0/0/0"
          * "GigabitEthernet0/0/0/1"
          * etc.
        """
        if nic_number == 1:
            return "MgmtEth0/0/CPU0/0"
        elif nic_number == 2:
            return "CtrlEth"
        elif nic_number == 3:
            return "DevEth"
        else:
            return "GigabitEthernet0/0/0/" + str(nic_number - 4)


Platform.PRODUCT_PLATFORM_MAP['com.cisco.ios-xrv9000'] = IOSXRv9000
# Some early releases of this platform instead used:
Platform.PRODUCT_PLATFORM_MAP['com.cisco.ios-xrv64'] = IOSXRv9000
