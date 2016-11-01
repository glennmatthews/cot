# September 2016, Glenn F. Matthews
# Copyright (c) 2013-2016 the COT project developers.
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

from COT.platforms.generic import GenericPlatform
from COT.data_validation import (
    ValueUnsupportedError, ValueTooLowError, ValueTooHighError,
    validate_int,
)

logger = logging.getLogger(__name__)


class CSR1000V(GenericPlatform):
    """Platform-specific logic for Cisco CSR1000V platform."""

    PLATFORM_NAME = "Cisco CSR1000V"

    CONFIG_TEXT_FILE = 'iosxe_config.txt'
    LITERAL_CLI_STRING = 'ios-config'
    # CSR1000v doesn't 'officially' support E1000, but it mostly works
    SUPPORTED_NIC_TYPES = ["E1000", "virtio", "VMXNET3"]

    @classmethod
    def controller_type_for_device(cls, device_type):
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
            return super(CSR1000V, cls).controller_type_for_device(device_type)

    @classmethod
    def guess_nic_name(cls, nic_number):
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

    @classmethod
    def validate_cpu_count(cls, cpus):
        """CSR1000V supports 1, 2, 4, or 8 CPUs.

        Args:
          cpus (int): Number of CPUs.

        Raises:
          ValueTooLowError: if ``cpus`` is less than 1
          ValueTooHighError: if ``cpus`` is more than 8
          ValueUnsupportedError: if ``cpus`` is an unsupported value
              between 1 and 8
        """
        validate_int(cpus, 1, 8, "CPUs")
        if cpus not in [1, 2, 4, 8]:
            raise ValueUnsupportedError("CPUs", cpus, [1, 2, 4, 8])

    @classmethod
    def validate_memory_amount(cls, mebibytes):
        """Minimum 2.5 GiB, max 8 GiB.

        Args:
          mebibytes (int): RAM, in MiB.

        Raises:
          ValueTooLowError: if ``mebibytes`` is less than 2560
          ValueTooHighError: if ``mebibytes`` is more than 8192
        """
        if mebibytes < 2560:
            raise ValueTooLowError("RAM", str(mebibytes) + " MiB", "2.5 GiB")
        elif mebibytes > 8192:
            raise ValueTooHighError("RAM", str(mebibytes) + " MiB", "8 GiB")

    @classmethod
    def validate_nic_count(cls, count):
        """CSR1000V requires 3 NICs and supports up to 26.

        Args:
          count (int): Number of NICs.

        Raises:
          ValueTooLowError: if ``count`` is less than 3
          ValueTooHighError: if ``count`` is more than 26
        """
        validate_int(count, 3, 26, "NIC count")

    @classmethod
    def validate_serial_count(cls, count):
        """CSR1000V supports 0-2 serial ports.

        Args:
          count (int): Number of serial ports.

        Raises:
          ValueTooLowError: if ``count`` is less than 0
          ValueTooHighError: if ``count`` is more than 2
        """
        validate_int(count, 0, 2, "serial ports")
