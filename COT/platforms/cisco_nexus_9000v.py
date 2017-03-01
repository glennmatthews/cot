# January 2017, Glenn F. Matthews
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

"""Platform logic for the Cisco Nexus 9000v virtual switch."""

import logging

from COT.platforms.platform import Platform, Hardware
from COT.data_validation import ValidRange

logger = logging.getLogger(__name__)


class Nexus9000v(Platform):
    """Platform-specific logic for Cisco Nexus 9000v."""

    PLATFORM_NAME = "Cisco Nexus 9000v"

    CONFIG_TEXT_FILE = 'nxos_config.txt'
    LITERAL_CLI_STRING = None
    SUPPORTED_NIC_TYPES = ["E1000", "VMXNET3"]

    HARDWARE_LIMITS = Platform.HARDWARE_LIMITS.copy()
    HARDWARE_LIMITS.update({
        Hardware.cpus: ValidRange(1, 4),
        Hardware.memory: ValidRange(8192, None),
        Hardware.nic_count: ValidRange(1, 65),
        Hardware.serial_count: ValidRange(1, 1),
    })

    def guess_nic_name(self, nic_number):
        """The Nexus 9000v has a management NIC and some number of data NICs.

        Args:
          nic_number (int): Nth NIC to name.

        Returns:
          * mgmt0
          * Ethernet1/1
          * Ethernet1/2
          * ...
        """
        if nic_number == 1:
            return "mgmt0"
        else:
            return "Ethernet1/{0}".format(nic_number - 1)


Platform.PRODUCT_PLATFORM_MAP['com.cisco.n9k'] = Nexus9000v
