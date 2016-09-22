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

"""Package describing the Cisco CSR1000V virtual router platform."""

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
        """CSR1000V uses SCSI for hard disks and IDE for CD-ROMs."""
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
        """
        return "GigabitEthernet" + str(nic_number)

    @classmethod
    def validate_cpu_count(cls, cpus):
        """CSR1000V supports 1, 2, or 4 CPUs."""
        validate_int(cpus, 1, 4, "CPUs")
        if cpus != 1 and cpus != 2 and cpus != 4:
            raise ValueUnsupportedError("CPUs", cpus, [1, 2, 4])

    @classmethod
    def validate_memory_amount(cls, mebibytes):
        """Minimum 2.5 GiB, max 8 GiB."""
        if mebibytes < 2560:
            raise ValueTooLowError("RAM", str(mebibytes) + " MiB", "2.5 GiB")
        elif mebibytes > 8192:
            raise ValueTooHighError("RAM", str(mebibytes) + " MiB", "8 GiB")

    @classmethod
    def validate_nic_count(cls, count):
        """CSR1000V requires 3 NICs and supports up to 26."""
        validate_int(count, 3, 26, "NICs")

    @classmethod
    def validate_serial_count(cls, count):
        """CSR1000V supports 0-2 serial ports."""
        validate_int(count, 0, 2, "serial ports")
