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

"""Platform logic for the Cisco NX-OSv virtual switch."""

import logging

from COT.platforms.generic import GenericPlatform
from COT.data_validation import (
    ValueTooLowError, ValueTooHighError, validate_int,
)

logger = logging.getLogger(__name__)


class NXOSv(GenericPlatform):
    """Platform-specific logic for Cisco NX-OSv (Titanium)."""

    PLATFORM_NAME = "Cisco NX-OSv"

    CONFIG_TEXT_FILE = 'nxos_config.txt'
    LITERAL_CLI_STRING = None
    SUPPORTED_NIC_TYPES = ["E1000", "virtio"]

    @classmethod
    def guess_nic_name(cls, nic_number):
        """NX-OSv names its NICs a bit interestingly...

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

    @classmethod
    def validate_cpu_count(cls, cpus):
        """NX-OSv requires 1-8 CPUs."""
        validate_int(cpus, 1, 8, "CPUs")

    @classmethod
    def validate_memory_amount(cls, mebibytes):
        """NX-OSv requires 2-8 GiB of RAM."""
        if mebibytes < 2048:
            raise ValueTooLowError("RAM", str(mebibytes) + " MiB", "2 GiB")
        elif mebibytes > 8192:
            raise ValueTooHighError("RAM", str(mebibytes) + " MiB", "8 GiB")

    @classmethod
    def validate_serial_count(cls, count):
        """NX-OSv requires 1-2 serial ports."""
        validate_int(count, 1, 2, "serial ports")
