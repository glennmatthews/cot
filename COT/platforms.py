#!/usr/bin/env python
#
# platforms.py - Module for methods related to variations between
#                guest platforms (Cisco CSR1000V, Cisco IOS XRv, etc.)
#
# October 2013, Glenn F. Matthews
# Copyright (c) 2013-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Handles behavior that varies between guest platforms.

**Classes**

.. autosummary::
  :nosignatures:

  GenericPlatform
  CSR1000V
  IOSv
  IOSXRv
  IOSXRvRP
  IOSXRvLC
  NXOSv
"""

from .data_validation import ValueUnsupportedError
from .data_validation import ValueTooLowError, ValueTooHighError
import logging

logger = logging.getLogger(__name__)


class GenericPlatform(object):
    """Generic class for operations that depend on guest platform.

    To be used whenever the guest is unrecognized or does not need
    special handling.
    """

    PLATFORM_NAME = "(unrecognized platform, generic)"

    # Default file name for text configuration file to embed
    CONFIG_TEXT_FILE = 'config.txt'
    # Most platforms do not support a secondary configuration file
    SECONDARY_CONFIG_TEXT_FILE = None
    # Most platforms do not support configuration properties in the environment
    LITERAL_CLI_STRING = 'config'

    # Most platforms use a CD-ROM for bootstrap configuration
    BOOTSTRAP_DISK_TYPE = 'cdrom'

    @classmethod
    def controller_type_for_device(cls, device_type):
        """Get the default controller type for the given device type."""
        # For most platforms IDE is the correct default.
        return 'ide'

    @classmethod
    def guess_nic_name(cls, nic_number):
        """Guess the name of the Nth NIC for this platform.

        Note that this counts from 1, not from 0!
        """
        return ("Ethernet" + str(nic_number))

    @classmethod
    def validate_cpu_count(cls, cpus):
        """Throw an error if the number of CPUs is not a supported value."""
        if cpus < 1:
            raise ValueTooLowError("CPUs", cpus, 1)

    @classmethod
    def validate_memory_amount(cls, megabytes):
        """Throw an error if the amount of RAM is not supported."""
        if megabytes < 1:
            raise ValueTooLowError("RAM", megabytes, 1)

    @classmethod
    def validate_nic_count(cls, count):
        """Throw an error if the number of NICs is not supported."""
        if count < 0:
            raise ValueTooLowError("NIC count", count, 0)

    @classmethod
    def validate_nic_type(cls, type_string):
        """Throw an error if the NIC type string is not supported."""
        # We only really know 3 possible NIC types at present
        cls.valid_list_only("NIC type", type_string.upper(),
                            ["E1000", "VIRTIO", "VMXNET3"])

    @classmethod
    def validate_serial_count(cls, count):
        """Throw an error if the number of serial ports is not supported."""
        if count < 0:
            raise ValueTooLowError("serial port count", count, 0)

    @classmethod
    def valid_list_only(cls, desc, val, supported_list):
        """Error if the given value is not an item in the provided list."""
        if val not in supported_list:
            raise ValueUnsupportedError(desc, val, supported_list)


class IOSXRv(GenericPlatform):
    """Platform-specific logic for Cisco IOS XRv platform."""

    PLATFORM_NAME = "Cisco IOS XRv"

    CONFIG_TEXT_FILE = 'iosxr_config.txt'
    SECONDARY_CONFIG_TEXT_FILE = 'iosxr_config_admin.txt'
    LITERAL_CLI_STRING = None

    @classmethod
    def guess_nic_name(cls, nic_number):
        """MgmtEth0/0/CPU0/0, GigabitEthernet0/0/0/0, Gig0/0/0/1, etc."""
        if nic_number == 1:
            return "MgmtEth0/0/CPU0/0"
        else:
            return ("GigabitEthernet0/0/0/" + str(nic_number - 2))

    @classmethod
    def validate_cpu_count(cls, cpus):
        """IOS XRv supports 1-8 CPUs."""
        if cpus < 1:
            raise ValueTooLowError("CPUs", cpus, 1)
        elif cpus > 8:
            raise ValueTooHighError("CPUs", cpus, 8)

    @classmethod
    def validate_memory_amount(cls, megabytes):
        """Minimum 3 GB, max 8 GB of RAM."""
        if megabytes < 3072:
            raise ValueTooLowError("RAM", str(megabytes) + "MB", "3GB")
        elif megabytes > 8192:
            raise ValueTooHighError("RAM", str(megabytes) + "MB", "8GB")

    @classmethod
    def validate_nic_count(cls, count):
        """IOS XRv requires at least one NIC."""
        if count < 1:
            raise ValueTooLowError("NIC count", count, 1)

    @classmethod
    def validate_nic_type(cls, type_string):
        """IOS XRv supports E1000 and virtio NICs."""
        cls.valid_list_only("NIC type", type_string.upper(),
                            ["E1000", "VIRTIO"])

    @classmethod
    def validate_serial_count(cls, count):
        """IOS XRv supports 1-4 serial ports."""
        if count < 1:
            raise ValueTooLowError("serial ports", count, 1)
        elif count > 4:
            raise ValueTooHighError("serial ports", count, 4)


class IOSXRvRP(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv HA-capable RP."""

    PLATFORM_NAME = "Cisco IOS XRv route processor card"

    @classmethod
    def guess_nic_name(cls, nic_number):
        """Fabric and management only.

        * fabric
        * MgmtEth0/{SLOT}/CPU0/0
        """
        if nic_number == 1:
            return "fabric"
        else:
            return ("MgmtEth0/{SLOT}/CPU0/" + str(nic_number - 2))

    @classmethod
    def validate_nic_count(cls, count):
        """Fabric plus an optional management NIC."""
        if count < 1:
            raise ValueTooLowError("NIC count", count, 1)
        if count > 2:
            raise ValueTooHighError("NIC count", count, 2)


class IOSXRvLC(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv line card."""

    PLATFORM_NAME = "Cisco IOS XRv line card"

    # No bootstrap config for LCs - they inherit from the RP
    CONFIG_TEXT_FILE = None
    SECONDARY_CONFIG_TEXT_FILE = None

    @classmethod
    def guess_nic_name(cls, nic_number):
        """Fabric interface plus slot-appropriate GigabitEthernet interfaces.

        * fabric
        * GigabitEthernet0/{SLOT}/0/0
        * GigabitEthernet0/{SLOT}/0/1
        * etc.
        """
        if nic_number == 1:
            return "fabric"
        else:
            return ("GigabitEthernet0/{SLOT}/0/" + str(nic_number - 2))

    @classmethod
    def validate_serial_count(cls, count):
        """No serial ports are needed but up to 4 can be used for debugging."""
        if count > 4:
            raise ValueTooHighError("serial ports", count, 4)


class CSR1000V(GenericPlatform):
    """Platform-specific logic for Cisco CSR1000V platform."""

    PLATFORM_NAME = "Cisco CSR1000V"

    CONFIG_TEXT_FILE = 'iosxe_config.txt'
    LITERAL_CLI_STRING = 'ios-config'

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
        return ("GigabitEthernet" + str(nic_number))

    @classmethod
    def validate_cpu_count(cls, cpus):
        """CSR1000V supports 1, 2, or 4 CPUs."""
        if cpus < 1:
            raise ValueTooLowError("CPUs", cpus, 1)
        elif cpus > 4:
            raise ValueTooHighError("CPUs", cpus, 4)
        elif cpus != 1 and cpus != 2 and cpus != 4:
            raise ValueUnsupportedError("CPUs", cpus, [1, 2, 4])

    @classmethod
    def validate_memory_amount(cls, megabytes):
        """Minimum 2.5 GB, max 8 GB."""
        if megabytes < 2560:
            raise ValueTooLowError("RAM", str(megabytes) + "MB", "2.5GB")
        elif megabytes > 8192:
            raise ValueTooHighError("RAM", str(megabytes) + "MB", "8GB")

    @classmethod
    def validate_nic_count(cls, count):
        """CSR1000V requires 3 NICs and supports up to 26."""
        if count < 3:
            raise ValueTooLowError("NICs", count, 3)
        elif count > 26:
            raise ValueTooHighError("NICs", count, 26)

    @classmethod
    def validate_serial_count(cls, count):
        """CSR1000V supports 0-2 serial ports."""
        if count < 0:
            raise ValueTooLowError("serial ports", count, 0)
        elif count > 2:
            raise ValueTooHighError("serial ports", count, 2)


class IOSv(GenericPlatform):
    """Platform-specific logic for Cisco IOSv."""

    PLATFORM_NAME = "Cisco IOSv"

    CONFIG_TEXT_FILE = 'ios_config.txt'
    LITERAL_CLI_STRING = None
    # IOSv has no CD-ROM driver so bootstrap configs must be provided on disk.
    BOOTSTRAP_DISK_TYPE = 'harddisk'

    @classmethod
    def guess_nic_name(cls, nic_number):
        """GigabitEthernet0/0, GigabitEthernet0/1, etc."""
        return ("GigabitEthernet0/" + str(nic_number - 1))

    @classmethod
    def validate_cpu_count(cls, cpus):
        """IOSv only supports a single CPU."""
        if cpus < 1:
            raise ValueTooLowError("CPUs", cpus, 1)
        elif cpus > 1:
            raise ValueTooHighError("CPUs", cpus, 1)

    @classmethod
    def validate_memory_amount(cls, megabytes):
        """IOSv has minimum 192 MB (with minimal feature set), max 3 GB."""
        if megabytes < 192:
            raise ValueTooLowError("RAM", str(megabytes) + "MB", "192MB")
        elif megabytes < 384:
            # Warn but allow
            logger.warning("Less than 384MB of RAM may not be sufficient "
                           "for some IOSv feature sets")
        elif megabytes > 3072:
            raise ValueTooHighError("RAM", str(megabytes) + "MB", "3GB")

    @classmethod
    def validate_nic_count(cls, count):
        """IOSv supports up to 16 NICs."""
        if count < 0:
            raise ValueTooLowError("NICs", count, 0)
        elif count > 16:
            raise ValueTooHighError("NICs", count, 16)

    @classmethod
    def validate_nic_type(cls, type_string):
        """IOSv only supports E1000 NICs."""
        if type_string.upper() != "E1000":
            raise ValueUnsupportedError("NIC type", type_string.upper(),
                                        "E1000")

    @classmethod
    def validate_serial_count(cls, count):
        """IOSv requires 1-2 serial ports."""
        if count < 1:
            raise ValueTooLowError("serial ports", count, 1)
        elif count > 2:
            raise ValueTooHighError("serial ports", count, 2)


class NXOSv(GenericPlatform):
    """Platform-specific logic for Cisco NX-OSv (Titanium)."""

    PLATFORM_NAME = "Cisco NX-OSv"

    CONFIG_TEXT_FILE = 'nxos_config.txt'
    LITERAL_CLI_STRING = None

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
        if cpus < 1:
            raise ValueTooLowError("CPUs", cpus, 1)
        elif cpus > 8:
            raise ValueTooHighError("CPUs", cpus, 8)

    @classmethod
    def validate_memory_amount(cls, megabytes):
        """NX-OSv requires 2-8 GB of RAM."""
        if megabytes < 2048:
            raise ValueTooLowError("RAM", str(megabytes) + "MB", "2GB")
        elif megabytes > 8192:
            raise ValueTooHighError("RAM", str(megabytes) + "MB", "8GB")

    @classmethod
    def validate_nic_type(cls, type_string):
        """NX-OSv supports only E1000 and virtio NICs."""
        # VMXNET3 is not supported
        cls.valid_list_only("NIC type", type_string.upper(),
                            ["E1000", "VIRTIO"])

    @classmethod
    def validate_serial_count(cls, count):
        """NX-OSv requires 1-2 serial ports."""
        if count < 1:
            raise ValueTooLowError("serial ports", count, 1)
        elif count > 2:
            raise ValueTooHighError("serial ports", count, 2)
