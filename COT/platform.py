#!/usr/bin/env python
#
# platform.py - Module for methods related to variations between
#               guest platforms (Cisco CSR1000V, Cisco IOS XRv, etc.)
#
# October 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

from .data_validation import ValueUnsupportedError
from .data_validation import ValueTooLowError, ValueTooHighError
import logging

logger = logging.getLogger('cot')

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
        """Return the default controller type (scsi/ide) for the given
        device type (harddisk/cdrom).
        """
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
        """Throw an error if the number of CPUs is not a supported value"""
        if cpus < 1:
            raise ValueTooLowError("CPUs", cpus, 1)


    @classmethod
    def validate_memory_amount(cls, megabytes):
        """Throw an error if the amount of RAM is not supported.
        """
        if megabytes < 1:
            raise ValueTooLowError("RAM", megabytes, 1)


    @classmethod
    def validate_nic_count(cls, count):
        """Throw an error if the number of NICs is not supported.
        """
        if count < 0:
            raise ValueTooLowError("NIC count", count, 0)

    @classmethod
    def validate_nic_type(cls, type_string):
        """Throw an error if the NIC type string is not supported.
        """
        # We only really know 3 possible NIC types at present
        cls.valid_list_only("NIC type", type_string.upper(),
                            ["E1000", "VIRTIO", "VMXNET3"])


    @classmethod
    def validate_serial_count(cls, count):
        """Throw an error if the number of serial ports is not supported.
        """
        if count < 0:
            raise ValueTooLowError("serial port count", count, 0)

    @classmethod
    def valid_list_only(cls, desc, val, supported_list):
        """Helper function - throw an error if the given value is not
        an item in the provided list.
        """
        if not val in supported_list:
            raise ValueUnsupportedError(desc, val, supported_list)


class IOSXRv(GenericPlatform):
    """Platform-specific logic for Cisco IOS XRv platform
    """
    PLATFORM_NAME = "Cisco IOS XRv"

    CONFIG_TEXT_FILE = 'iosxr_config.txt'
    SECONDARY_CONFIG_TEXT_FILE = 'iosxr_config_admin.txt'
    LITERAL_CLI_STRING = None

    @classmethod
    def guess_nic_name(cls, nic_number):
        # MgmtEthernet0/0/CPU0/0, GigabitEthernet0/0/0/0, Gig0/0/0/1, etc.
        if nic_number == 1:
            return "MgmtEthernet0/0/CPU0/0"
        else:
            return ("GigabitEthernet0/0/0/" + str(nic_number - 2))

    @classmethod
    def validate_cpu_count(cls, cpus):
        if cpus < 1:
            raise ValueTooLowError("CPUs", cpus, 1)
        elif cpus > 8:
            raise ValueTooHighError("CPUs", cpus, 8)


    @classmethod
    def validate_memory_amount(cls, megabytes):
        # Minimum 3 GB, max 8 GB
        if megabytes < 3072:
            raise ValueTooLowError("RAM", str(megabytes) + "MB", "3GB")
        elif megabytes > 8192:
            raise ValueTooHighError("RAM", str(megabytes) + "MB", "8GB")

    @classmethod
    def validate_nic_count(cls, count):
        if count < 1:
            raise ValueTooLowError("NIC count", count, 1)

    @classmethod
    def validate_nic_type(cls, type_string):
        # VMXNET3 is not supported
        cls.valid_list_only("NIC type", type_string.upper(),
                            ["E1000", "VIRTIO"])

    @classmethod
    def validate_serial_count(cls, count):
        if count < 1:
            raise ValueTooLowError("serial ports", count, 1)
        elif count > 4:
            raise ValueTooHighError("serial ports", count, 4)


class IOSXRvRP(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv HA-capable RP
    """
    PLATFORM_NAME = "Cisco IOS XRv route processor card"

    @classmethod
    def guess_nic_name(cls, nic_number):
        # First NIC name is fabric - then as above
        if nic_number == 1:
            return "fabric"
        else:
            return IOSXRv.guess_nic_name(nic_number - 1)


class IOSXRvLC(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv line card
    """
    PLATFORM_NAME = "Cisco IOS XRv line card"

    # No bootstrap config for LCs - they inherit from the RP
    CONFIG_TEXT_FILE = None
    SECONDARY_CONFIG_TEXT_FILE = None

    @classmethod
    def guess_nic_name(cls, nic_number):
        # fabric, GigabitEthernet0/2/0/0, Gig0/2/0/1, etc.
        if nic_number == 1:
            return "fabric"
        else:
            return ("GigabitEthernet0/2/0/" + str(nic_number - 2))

    @classmethod
    def validate_serial_count(cls, count):
        """An LC can run with no serial ports at all"""
        if count > 4:
            raise ValueTooHighError("serial ports", count, 4)


class CSR1000V(GenericPlatform):
    """Platform-specific logic for Cisco CSR1000V platform
    """
    PLATFORM_NAME = "Cisco CSR1000V"

    CONFIG_TEXT_FILE = 'iosxe_config.txt'
    LITERAL_CLI_STRING = 'ios-config'

    @classmethod
    def controller_type_for_device(cls, device_type):
        if device_type == 'harddisk':
            return 'scsi'
        elif device_type == 'cdrom':
            return 'ide'
        else:
            return super(CSR1000V, cls).controller_type_for_device(device_type)


    @classmethod
    def guess_nic_name(cls, nic_number):
        # In all current CSR releases, NICs start at GigabitEthernet1
        # Some early versions started at GigabitEthernet0 but we don't
        # support that...
        return ("GigabitEthernet" + str(nic_number))


    @classmethod
    def validate_cpu_count(cls, cpus):
        # Only one and four CPUs are supported at present
        if cpus < 1:
            raise ValueTooLowError("CPUs", cpus, 1)
        elif cpus > 4:
            raise ValueTooHighError("CPUs", cpus, 4)
        elif cpus != 1 and cpus != 2 and cpus != 4:
            raise ValueUnsupportedError("CPUs", cpus, [1, 2, 4])


    @classmethod
    def validate_memory_amount(cls, megabytes):
        # Minimum 2.5 GB, max 8 GB
        if megabytes < 2560:
            raise ValueTooLowError("RAM", str(megabytes) + "MB", "2.5GB")
        elif megabytes > 8192:
            raise ValueTooHighError("RAM", str(megabytes) + "MB", "8GB")


    @classmethod
    def validate_nic_count(cls, count):
        if count < 3:
            raise ValueTooLowError("NICs", count, 3)
        elif count > 26:
            raise ValueTooHighError("NICs", count, 26)

    @classmethod
    def validate_serial_count(cls, count):
        # Serial port is OPTIONAL on CSR1000V
        if count < 0:
            raise ValueTooLowError("serial ports", count, 0)
        elif count > 2:
            raise ValueTooHighError("serial ports", count, 2)


class IOSv(GenericPlatform):
    """Platform-specific logic for Cisco IOSv
    """
    PLATFORM_NAME = "Cisco IOSv"

    CONFIG_TEXT_FILE = 'ios_config.txt'
    LITERAL_CLI_STRING = None
    # IOSv has no CD-ROM driver so bootstrap configs must be provided on disk.
    BOOTSTRAP_DISK_TYPE = 'harddisk'

    @classmethod
    def guess_nic_name(cls, nic_number):
        # GigabitEthernet0/0, GigabitEthernet0/1, etc.
        return ("GigabitEthernet0/" + str(nic_number - 1))


    @classmethod
    def validate_cpu_count(cls, cpus):
        if cpus < 1:
            raise ValueTooLowError("CPUs", cpus, 1)
        elif cpus > 1:
            raise ValueTooHighError("CPUs", cpus, 1)

    @classmethod
    def validate_memory_amount(cls, megabytes):
        # Minimum 192 MB (with minimal feature set), max 3 GB
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
        if count < 0:
            raise ValueTooLowError("NICs", count, 0)
        elif count > 16:
            raise ValueTooHighError("NICs", count, 16)

    @classmethod
    def validate_nic_type(cls, type_string):
        # Only E1000 is supported
        if type_string.upper() != "E1000":
            raise ValueUnsupportedError("NIC type", type_string.upper(),
                                        "E1000")

    @classmethod
    def validate_serial_count(cls, count):
        if count < 1:
            raise ValueTooLowError("serial ports", count, 1)
        elif count > 2:
            raise ValueTooHighError("serial ports", count, 2)


class NXOSv(GenericPlatform):
    """Platform-specific logic for Cisco NX-OSv (Titanium)
    """
    PLATFORM_NAME = "Cisco NX-OSv"

    CONFIG_TEXT_FILE = 'nxos_config.txt'
    LITERAL_CLI_STRING = None

    @classmethod
    def guess_nic_name(cls, nic_number):
        # mgmt0, Ethernet2/1, Ethernet2/2, etc.
        if nic_number == 1:
            return "mgmt0"
        else:
            return ("Ethernet{0}/{1}".format((nic_number - 2) // 48 + 2,
                                             (nic_number - 2) % 48 + 1))

    @classmethod
    def validate_cpu_count(cls, cpus):
        if cpus < 1:
            raise ValueTooLowError("CPUs", cpus, 1)
        elif cpus > 8:
            raise ValueTooHighError("CPUs", cpus, 8)

    @classmethod
    def validate_memory_amount(cls, megabytes):
        # Minimum 2 GB, max 8 GB
        if megabytes < 2048:
            raise ValueTooLowError("RAM", str(megabytes) + "MB", "2GB")
        elif megabytes > 8192:
            raise ValueTooHighError("RAM", str(megabytes) + "MB", "8GB")

    @classmethod
    def validate_nic_type(cls, type_string):
        # VMXNET3 is not supported
        cls.valid_list_only("NIC type", type_string.upper(),
                            ["E1000", "VIRTIO"])

    @classmethod
    def validate_serial_count(cls, count):
        if count < 1:
            raise ValueTooLowError("serial ports", count, 1)
        elif count > 2:
            raise ValueTooHighError("serial ports", count, 2)
