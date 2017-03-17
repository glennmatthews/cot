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

"""Platform logic for the Cisco IOSv virtual router."""

import logging

from COT.platforms.platform import Platform, Hardware
from COT.data_validation import ValidRange

logger = logging.getLogger(__name__)


class IOSv(Platform):
    """Platform-specific logic for Cisco IOSv."""

    PLATFORM_NAME = "Cisco IOSv"

    CONFIG_TEXT_FILE = 'ios_config.txt'
    LITERAL_CLI_STRING = None
    # IOSv has no CD-ROM driver so bootstrap configs must be provided on disk.
    BOOTSTRAP_DISK_TYPE = 'harddisk'
    SUPPORTED_NIC_TYPES = ["E1000"]

    HARDWARE_LIMITS = Platform.HARDWARE_LIMITS.copy()
    HARDWARE_LIMITS.update({
        Hardware.cpus: ValidRange(1, 1),
        Hardware.memory: ValidRange(192, 3072),   # but see also below
        Hardware.nic_count: ValidRange(0, 16),
        Hardware.serial_count: ValidRange(1, 2),
    })

    def guess_nic_name(self, nic_number):
        """GigabitEthernet0/0, GigabitEthernet0/1, etc.

        Args:
          nic_number (int): Nth NIC to name.
        Returns:
          * "GigabitEthernet0/0"
          * "GigabitEthernet0/1"
          * etc.
        """
        return "GigabitEthernet0/" + str(nic_number - 1)

    def validate_memory_amount(self, mebibytes):
        """IOSv has minimum 192 MiB (with minimal feature set), max 3 GiB.

        Args:
          mebibytes (int): RAM, in MiB.

        Raises:
          ValueTooLowError: if ``mebibytes`` is less than 192
          ValueTooHighError: if ``mebibytes`` is more than 3072
        """
        previously_validated = (mebibytes in
                                self._already_validated[Hardware.memory])
        super(IOSv, self).validate_memory_amount(mebibytes)
        if mebibytes < 384 and not previously_validated:
            # Warn but allow
            logger.warning("Less than 384MiB of RAM may not be sufficient "
                           "for some IOSv feature sets")


Platform.PRODUCT_PLATFORM_MAP['com.cisco.iosv'] = IOSv
