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

from COT.platforms.generic import GenericPlatform
from COT.data_validation import (
    ValueTooLowError, validate_int,
)

logger = logging.getLogger(__name__)


class Nexus9000v(GenericPlatform):
    """Platform-specific logic for Cisco Nexus 9000v."""

    PLATFORM_NAME = "Cisco Nexus 9000v"

    CONFIG_TEXT_FILE = 'nxos_config.txt'
    LITERAL_CLI_STRING = None
    SUPPORTED_NIC_TYPES = ["E1000", "VMXNET3"]

    @classmethod
    def guess_nic_name(cls, nic_number):
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

    @classmethod
    def validate_cpu_count(cls, cpus):
        """The Nexus 9000v requires 1-4 vCPUs.

        Args:
          cpus (int): Number of vCPUs

        Raises:
          ValueTooLowError: if ``cpus`` is less than 1
          ValueTooHighError: if ``cpus`` is more than 4
        """
        validate_int(cpus, 1, 4, "CPUs")

    @classmethod
    def validate_memory_amount(cls, mebibytes):
        """The Nexus 9000v requires at least 8 GiB of RAM.

        Args:
          mebibytes (int): RAM, in MiB.

        Raises:
          ValueTooLowError: if ``mebibytes`` is less than 8192
        """
        if mebibytes < 8192:
            raise ValueTooLowError("RAM", str(mebibytes) + " MiB", "8 GiB")

    @classmethod
    def validate_nic_count(cls, count):
        """The Nexus 9000v requires at least 1 and supports at most 65 NICs.

        Args:
          count (int): Number of NICs.

        Raises:
          ValueTooLowError: if ``count`` is less than 1
          ValueTooHighError: if ``count`` is more than 65
        """
        validate_int(count, 1, 65, "NICs")

    @classmethod
    def validate_serial_count(cls, count):
        """The Nexus 9000v requires exactly 1 serial port.

        Args:
          count (int): Number of serial ports.

        Raises:
          ValueTooLowError: if ``count`` is less than 1
          ValueTooHighError: if ``count`` is more than 1
        """
        validate_int(count, 1, 1, "serial ports")
