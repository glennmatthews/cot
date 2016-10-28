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

"""Platform logic for the Cisco IOS XRv virtual router and its variants.

**Classes**

.. autosummary::
   :nosignatures:

   IOSXRv
   IOSXRvLC
   IOSXRvRP
"""

import logging

from COT.platforms.generic import GenericPlatform
from COT.data_validation import (
    ValueTooLowError, ValueTooHighError, validate_int,
)

logger = logging.getLogger(__name__)


class IOSXRv(GenericPlatform):
    """Platform-specific logic for Cisco IOS XRv platform."""

    PLATFORM_NAME = "Cisco IOS XRv"

    CONFIG_TEXT_FILE = 'iosxr_config.txt'
    SECONDARY_CONFIG_TEXT_FILE = 'iosxr_config_admin.txt'
    LITERAL_CLI_STRING = None
    SUPPORTED_NIC_TYPES = ["E1000", "virtio"]

    @classmethod
    def guess_nic_name(cls, nic_number):
        """MgmtEth0/0/CPU0/0, GigabitEthernet0/0/0/0, Gig0/0/0/1, etc.

        :param int nic_number: Nth NIC to name.
        :return:
          * "MgmtEth0/0/CPU0/0"
          * "GigabitEthernet0/0/0/0"
          * "GigabitEthernet0/0/0/1"
          * etc.
        """
        if nic_number == 1:
            return "MgmtEth0/0/CPU0/0"
        else:
            return "GigabitEthernet0/0/0/" + str(nic_number - 2)

    @classmethod
    def validate_cpu_count(cls, cpus):
        """IOS XRv supports 1-8 CPUs.

        :param int cpus: Number of CPUs
        :raises ValueTooLowError: if ``cpus`` is less than 1
        :raises ValueTooHighError: if ``cpus`` is more than 8
        """
        validate_int(cpus, 1, 8, "CPUs")

    @classmethod
    def validate_memory_amount(cls, mebibytes):
        """Minimum 3 GiB, max 8 GiB of RAM.

        :param int mebibytes: RAM, in MiB.
        :raises ValueTooLowError: if``mebibytes`` is less than 3072
        :raises ValueTooHighError: if ``mebibytes`` is more than 8192
        """
        if mebibytes < 3072:
            raise ValueTooLowError("RAM", str(mebibytes) + " MiB", "3 GiB")
        elif mebibytes > 8192:
            raise ValueTooHighError("RAM", str(mebibytes) + " MiB", " 8GiB")

    @classmethod
    def validate_nic_count(cls, count):
        """IOS XRv requires at least one NIC.

        :param int count: Number of NICs.
        :raises ValueTooLowError: if ``count`` is less than 1
        """
        validate_int(count, 1, None, "NIC count")

    @classmethod
    def validate_serial_count(cls, count):
        """IOS XRv supports 1-4 serial ports.

        :param int count: Number of serial ports.
        :raises ValueTooLowError: if ``count`` is less than 1
        :raises ValueTooHighError: if ``count`` is more than 4
        """
        validate_int(count, 1, 4, "serial ports")


class IOSXRvRP(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv HA-capable RP."""

    PLATFORM_NAME = "Cisco IOS XRv route processor card"

    @classmethod
    def guess_nic_name(cls, nic_number):
        """Fabric and management only.

        :param int nic_number: Nth NIC to name.
        :return: "fabric" or "MgmtEth0/{SLOT}/CPU0/0" only
        """
        if nic_number == 1:
            return "fabric"
        else:
            return "MgmtEth0/{SLOT}/CPU0/" + str(nic_number - 2)

    @classmethod
    def validate_nic_count(cls, count):
        """Fabric plus an optional management NIC.

        :param int count: Number of NICs.
        :raises ValueTooLowError: if ``count`` is less than 1
        :raises ValueTooHighError: if ``count`` is more than 2
        """
        validate_int(count, 1, 2, "NIC count")


class IOSXRvLC(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv line card."""

    PLATFORM_NAME = "Cisco IOS XRv line card"

    # No bootstrap config for LCs - they inherit from the RP
    CONFIG_TEXT_FILE = None
    SECONDARY_CONFIG_TEXT_FILE = None

    @classmethod
    def guess_nic_name(cls, nic_number):
        """Fabric interface plus slot-appropriate GigabitEthernet interfaces.

        :param int nic_number: Nth NIC to name.
        :return:
          * "fabric"
          * "GigabitEthernet0/{SLOT}/0/0"
          * "GigabitEthernet0/{SLOT}/0/1"
          * etc.
        """
        if nic_number == 1:
            return "fabric"
        else:
            return "GigabitEthernet0/{SLOT}/0/" + str(nic_number - 2)

    @classmethod
    def validate_serial_count(cls, count):
        """No serial ports are needed but up to 4 can be used for debugging.

        :param int count: Number of serial ports.
        :raises ValueTooLowError: if ``count`` is less than 0
        :raises ValueTooHighError: if ``count`` is more than 4
        """
        validate_int(count, 0, 4, "serial ports")
