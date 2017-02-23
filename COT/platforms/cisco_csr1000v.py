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

"""Platform logic for the Cisco CSR1000V virtual router."""

import logging

from COT.platforms.platform import Platform, Hardware
from COT.data_validation import ValueUnsupportedError, ValidRange

logger = logging.getLogger(__name__)


class CSR1000V(Platform):
    """Platform-specific logic for Cisco CSR1000V platform."""

    PLATFORM_NAME = "Cisco CSR1000V"

    CONFIG_TEXT_FILE = 'iosxe_config.txt'
    LITERAL_CLI_STRING = 'ios-config'
    # CSR1000v doesn't 'officially' support E1000, but it mostly works
    SUPPORTED_NIC_TYPES = ["E1000", "virtio", "VMXNET3"]

    HARDWARE_LIMITS = Platform.HARDWARE_LIMITS.copy()
    HARDWARE_LIMITS.update({
        Hardware.cpus: ValidRange(1, 8),    # but see below
        Hardware.memory: ValidRange(2560, 8192),
        Hardware.nic_count: ValidRange(3, 26),
        Hardware.serial_count: ValidRange(0, 2),
    })

    def controller_type_for_device(self, device_type):
        """CSR1000V uses SCSI for hard disks and IDE for CD-ROMs.

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
            return super(CSR1000V, self).controller_type_for_device(
                device_type)

    def guess_nic_name(self, nic_number):
        """GigabitEthernet1, GigabitEthernet2, etc.

        .. warning::
          In all current CSR releases, NIC names start at "GigabitEthernet1".
          Some early versions started at "GigabitEthernet0" but we don't
          support that.

        Args:
          nic_number (int): Nth NIC to name.
        Returns:
          * "GigabitEthernet1"
          * "GigabitEthernet2"
          * etc.
        """
        return "GigabitEthernet" + str(nic_number)

    def validate_cpu_count(self, cpus):
        """CSR1000V supports 1, 2, 4, or 8 CPUs.

        Args:
          cpus (int): Number of CPUs.

        Raises:
          ValueTooLowError: if ``cpus`` is less than 1
          ValueTooHighError: if ``cpus`` is more than 8
          ValueUnsupportedError: if ``cpus`` is an unsupported value
              between 1 and 8
        """
        super(CSR1000V, self).validate_cpu_count(cpus)
        if cpus not in [1, 2, 4, 8]:
            raise ValueUnsupportedError("CPUs", cpus, [1, 2, 4, 8])


Platform.PRODUCT_PLATFORM_MAP['com.cisco.csr1000v'] = CSR1000V
