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

"""Platform logic for the Cisco NX-OSv virtual switch."""

import logging

from COT.platforms.platform import Platform, Hardware
from COT.data_validation import ValidRange

logger = logging.getLogger(__name__)


class NXOSv(Platform):
    """Platform-specific logic for Cisco NX-OSv (Titanium)."""

    PLATFORM_NAME = "Cisco NX-OSv"

    CONFIG_TEXT_FILE = 'nxos_config.txt'
    LITERAL_CLI_STRING = None
    SUPPORTED_NIC_TYPES = ["E1000", "virtio"]

    HARDWARE_LIMITS = Platform.HARDWARE_LIMITS.copy()
    HARDWARE_LIMITS.update({
        Hardware.cpus: ValidRange(1, 8),
        Hardware.memory: ValidRange(2048, 8192),
        Hardware.serial_count: ValidRange(1, 2),
    })

    def guess_nic_name(self, nic_number):
        """NX-OSv names its NICs a bit interestingly...

        Args:
          nic_number (int): Nth NIC to name.

        Returns:
          * mgmt0
          * Ethernet2/1
          * Ethernet2/2
          * ...
          * Ethernet2/48
          * Ethernet3/1
          * Ethernet3/2
          * ...
        """
        if nic_number == 1:
            return "mgmt0"
        else:
            return ("Ethernet{0}/{1}".format((nic_number - 2) // 48 + 2,
                                             (nic_number - 2) % 48 + 1))


Platform.PRODUCT_PLATFORM_MAP['com.cisco.nx-osv'] = NXOSv
