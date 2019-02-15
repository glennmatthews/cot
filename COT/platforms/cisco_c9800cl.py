# February 2019, Subba Srinivas
# Copyright (c) 2019 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Platform logic for the Cisco C9800-CL Wireless Lan Controller."""

import logging

from COT.platforms.platform import Platform, Hardware
from COT.data_validation import ValueUnsupportedError, ValidRange

logger = logging.getLogger(__name__)


class C9800CL(Platform):
    """Platform-specific logic for Cisco C9800-CL platform."""

    PLATFORM_NAME = "Cisco C9800-CL"

    CONFIG_TEXT_FILE = 'iosxe_config.txt'
    LITERAL_CLI_STRING = 'ios-config'
    # C9800CL doesn't 'officially' support E1000, but it mostly works
    SUPPORTED_NIC_TYPES = ["E1000", "virtio", "VMXNET3"]

    HARDWARE_LIMITS = Platform.HARDWARE_LIMITS.copy()
    HARDWARE_LIMITS.update({
        Hardware.cpus: ValidRange(4, 10),
        Hardware.memory: ValidRange(8192, 32768),
        Hardware.nic_count: ValidRange(1, 3),
        Hardware.serial_count: ValidRange(0, 2),
    })

    def controller_type_for_device(self, device_type):
        """C9800CL uses SCSI for hard disks and IDE for CD-ROMs.

        Args:
          device_type (str): 'harddisk' or 'cdrom'
        Returns:
          str: 'ide' for CD-ROM, 'scsi' for hard disk
        """
        if device_type == 'harddisk':
            return 'scsi'
        elif device_type == 'cdrom':
            return 'ide'
        else:
            return super(C9800CL, self).controller_type_for_device(
                device_type)

    def guess_nic_name(self, nic_number):
        """GigabitEthernet1, GigabitEthernet2, etc.

        Args:
          nic_number (int): Nth NIC to name.
        Returns:
          * "GigabitEthernet1"
          * "GigabitEthernet2"
          * etc.
        """
        return "GigabitEthernet" + str(nic_number)

    def validate_cpu_count(self, cpus):
        """C9800CL supports 4,6 or 10 CPUs.

        Args:
          cpus (int): Number of CPUs.

        Raises:
          ValueTooLowError: if ``cpus`` is less than 4
          ValueTooHighError: if ``cpus`` is more than 10
          ValueUnsupportedError: if ``cpus`` is a value other than 4, 6, 10
        """
        super(C9800CL, self).validate_cpu_count(cpus)
        if cpus not in [4, 6, 10]:
            raise ValueUnsupportedError("CPUs", cpus, [4, 6, 10])


Platform.PRODUCT_PLATFORM_MAP['com.cisco.vwlc'] = C9800CL
