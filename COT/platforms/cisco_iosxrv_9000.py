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

"""Platform logic for the Cisco IOS XRv 9000 virtual router."""

import logging

from COT.platforms.cisco_iosxrv import IOSXRv
from COT.data_validation import (
    ValueTooLowError, ValueTooHighError, validate_int,
)

logger = logging.getLogger(__name__)


class IOSXRv9000(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv 9000 platform."""

    PLATFORM_NAME = "Cisco IOS XRv 9000"
    SUPPORTED_NIC_TYPES = ["E1000", "virtio", "VMXNET3"]

    @classmethod
    def guess_nic_name(cls, nic_number):
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

    @classmethod
    def validate_cpu_count(cls, cpus):
        """Minimum 1, maximum 32 CPUs.

        Args:
          cpus (int): Number of CPUs

        Raises:
          ValueTooLowError: if ``cpus`` is less than 1
          ValueTooHighError: if ``cpus`` is more than 32
        """
        validate_int(cpus, 1, 32, "CPUs")

    @classmethod
    def validate_memory_amount(cls, mebibytes):
        """Minimum 8 GiB, maximum 32 GiB.

        Args:
          mebibytes (int): RAM, in MiB.

        Raises:
          ValueTooLowError: if ``mebibytes`` is less than 8192
          ValueTooHighError: if ``mebibytes`` is more than 32768
        """
        if mebibytes < 8192:
            raise ValueTooLowError("RAM", str(mebibytes) + " MiB", "8 GiB")
        elif mebibytes > 32768:
            raise ValueTooHighError("RAM", str(mebibytes) + " MiB", "32 GiB")

    @classmethod
    def validate_nic_count(cls, count):
        """IOS XRv 9000 requires at least 4 NICs.

        Args:
          count (int): Number of NICs.

        Raises:
          ValueTooLowError: if ``count`` is less than 4
        """
        validate_int(count, 4, None, "NIC count")
