#!/usr/bin/env python
#
# platforms.py - Module for methods related to variations between
#                guest platforms (Cisco CSR1000V, Cisco IOS XRv, etc.)
#
# October 2013, Glenn F. Matthews
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

"""Handles behavior that varies between guest platforms.

**Functions**

.. autosummary::
  :nosignatures:

  is_known_product_class
  platform_from_product_class

**Classes**

.. autosummary::
  :nosignatures:

  GenericPlatform
  CSR1000V
  IOSv
  IOSXRv
  IOSXRvRP
  IOSXRvLC
  IOSXRv9000
  NXOSv

**Constants**

.. autosummary::
  PRODUCT_PLATFORM_MAP
"""

import logging

from COT.data_validation import (
    validate_int,
    ValueUnsupportedError, ValueTooLowError, ValueTooHighError,
    NIC_TYPES,
)

logger = logging.getLogger(__name__)


def is_known_product_class(product_class):
    """Determine if the given product class string is a known one.

    :param str product_class: String like 'com.cisco.csr1000v'
    :return: True if the class is in :data:`PRODUCT_PLATFORM_MAP`, else False
    """
    return product_class in PRODUCT_PLATFORM_MAP


def platform_from_product_class(product_class):
    """Get the class of Platform corresponding to a product class string.

    :param str product_class: String like 'com.cisco.csr1000v'
    :return: Best guess of the appropriate platform based on
      :data:`PRODUCT_PLATFORM_MAP`, defaulting to
      :class:`GenericPlatform` if no better guess exists.
    :rtype: class
    """
    if product_class is None:
        return GenericPlatform
    if is_known_product_class(product_class):
        return PRODUCT_PLATFORM_MAP[product_class]
    logger.warning("Unrecognized product class '%s' - known classes "
                   "are %s. Treating as a generic platform",
                   product_class, PRODUCT_PLATFORM_MAP.keys())
    return GenericPlatform


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

    SUPPORTED_NIC_TYPES = NIC_TYPES

    # Valid value ranges - may be overridden by subclasses
    CPU_MIN = 1
    CPU_MAX = None
    RAM_MIN = 1
    RAM_MAX = None
    NIC_MIN = 0
    NIC_MAX = None
    SER_MIN = 0
    SER_MAX = None

    # Some of these methods are semi-abstract, so:
    # pylint: disable=unused-argument
    @classmethod
    def controller_type_for_device(cls, device_type):
        """Get the default controller type for the given device type.

        :param str device_type: 'harddisk', 'cdrom', etc.
        :return: 'ide' unless overridden by subclass.
        """
        # For most platforms IDE is the correct default.
        return 'ide'

    @classmethod
    def guess_nic_name(cls, nic_number):
        """Guess the name of the Nth NIC for this platform.

        .. note:: This method counts from 1, not from 0!

        :param int nic_number: Nth NIC to name.
        :return: "Ethernet1", "Ethernet2", etc. unless overridden by subclass.
        """
        return "Ethernet" + str(nic_number)

    @classmethod
    def validate_cpu_count(cls, cpus):
        """Throw an error if the number of CPUs is not a supported value.

        :param int cpus: Number of CPUs
        :raises ValueTooLowError: if ``cpus`` is less than :const:`CPU_MIN`
        :raises ValueTooHighError: if ``cpus`` is more than :const:`CPU_MAX`
        """
        validate_int(cpus, cls.CPU_MIN, cls.CPU_MAX, "CPUs")

    @classmethod
    def validate_memory_amount(cls, mebibytes):
        """Throw an error if the amount of RAM is not supported.

        :param int mebibytes: RAM, in MiB.
        :raises ValueTooLowError: if :attr:`mebibytes` is less than
          :const:`RAM_MIN`
        :raises ValueTooHighError: if :attr:`mebibytes` is more than
          :const:`RAM_MAX`
        """
        if cls.RAM_MIN is not None and mebibytes < cls.RAM_MIN:
            if cls.RAM_MIN > 1024 and cls.RAM_MIN % 1024 == 0:
                raise ValueTooLowError("RAM", str(mebibytes) + " MiB",
                                       str(cls.RAM_MIN / 1024) + " GiB")
            else:
                raise ValueTooLowError("RAM", str(mebibytes) + " MiB",
                                       str(cls.RAM_MIN) + " MiB")
        if cls.RAM_MAX is not None and mebibytes > cls.RAM_MAX:
            if cls.RAM_MAX > 1024 and cls.RAM_MAX % 1024 == 0:
                raise ValueTooHighError("RAM", str(mebibytes) + " MiB",
                                        str(cls.RAM_MAX / 1024) + " GiB")
            else:
                raise ValueTooHighError("RAM", str(mebibytes) + " MiB",
                                        str(cls.RAM_MAX) + " MiB")

    @classmethod
    def validate_nic_count(cls, count):
        """Throw an error if the number of NICs is not supported.

        :param int count: Number of NICs.
        :raises ValueTooLowError: if ``count`` is less than :const:`NIC_MIN`
        :raises ValueTooHighError: if ``count`` is more than :const:`NIC_MAX`
        """
        validate_int(count, cls.NIC_MIN, cls.NIC_MAX, "NIC count")

    @classmethod
    def validate_nic_type(cls, type_string):
        """Throw an error if the NIC type string is not supported.

        .. seealso::
           - :func:`COT.data_validation.canonicalize_nic_subtype`
           - :data:`COT.data_validation.NIC_TYPES`

        :param str type_string: See :data:`COT.data_validation.NIC_TYPES`
        :raises ValueUnsupportedError: if ``type_string`` is not in
          :const:`SUPPORTED_NIC_TYPES`
        """
        if type_string not in cls.SUPPORTED_NIC_TYPES:
            raise ValueUnsupportedError("NIC type", type_string,
                                        cls.SUPPORTED_NIC_TYPES)

    @classmethod
    def validate_nic_types(cls, type_list):
        """Throw an error if any NIC type string in the list is unsupported.

        :param list type_list: See :data:`COT.data_validation.NIC_TYPES`
        :raises ValueUnsupportedError: if any value in ``type_list`` is not in
          :const:`SUPPORTED_NIC_TYPES`
        """
        for type_string in type_list:
            cls.validate_nic_type(type_string)

    @classmethod
    def validate_serial_count(cls, count):
        """Throw an error if the number of serial ports is not supported.

        :param int count: Number of serial ports.
        :raises ValueTooLowError: if ``count`` is less than :const:`SER_MIN`
        :raises ValueTooHighError: if ``count`` is more than :const:`SER_MAX`
        """
        validate_int(count, cls.SER_MIN, cls.SER_MAX, "serial port count")


class IOSXRv(GenericPlatform):
    """Platform-specific logic for Cisco IOS XRv platform."""

    PLATFORM_NAME = "Cisco IOS XRv"

    CONFIG_TEXT_FILE = 'iosxr_config.txt'
    SECONDARY_CONFIG_TEXT_FILE = 'iosxr_config_admin.txt'
    LITERAL_CLI_STRING = None
    SUPPORTED_NIC_TYPES = ["E1000", "virtio"]

    # IOS XRv supports 1-8 CPUs.
    CPU_MAX = 8
    # Minimum 3 GiB, max 8 GiB of RAM.
    RAM_MIN = 3072
    RAM_MAX = 8192
    # IOS XRv requires at least one NIC.
    NIC_MIN = 1
    # IOS XRv supports 1-4 serial ports.
    SER_MIN = 1
    SER_MAX = 4

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


class IOSXRvRP(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv HA-capable RP."""

    PLATFORM_NAME = "Cisco IOS XRv route processor card"

    # Fabric plus an optional management NIC.
    NIC_MIN = 1
    NIC_MAX = 2

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


class IOSXRvLC(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv line card."""

    PLATFORM_NAME = "Cisco IOS XRv line card"

    # No bootstrap config for LCs - they inherit from the RP
    CONFIG_TEXT_FILE = None
    SECONDARY_CONFIG_TEXT_FILE = None

    # No serial ports are needed but up to 4 can be used for debugging.
    SER_MIN = 0

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


class IOSXRv9000(IOSXRv):
    """Platform-specific logic for Cisco IOS XRv 9000 platform."""

    PLATFORM_NAME = "Cisco IOS XRv 9000"
    SUPPORTED_NIC_TYPES = ["E1000", "virtio", "VMXNET3"]

    # Minimum 1, maximum 32 CPUs.
    CPU_MAX = 32
    # Minimum 8 GiB, maximum 32 GiB.
    RAM_MIN = 8192
    RAM_MAX = 32768
    # IOS XRv 9000 requires at least 4 NICs.
    NIC_MIN = 4

    @classmethod
    def guess_nic_name(cls, nic_number):
        """MgmtEth0/0/CPU0/0, CtrlEth, DevEth, GigabitEthernet0/0/0/0, etc.

        :param int nic_number: Nth NIC to name.
        :return:
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


class CSR1000V(GenericPlatform):
    """Platform-specific logic for Cisco CSR1000V platform."""

    PLATFORM_NAME = "Cisco CSR1000V"

    CONFIG_TEXT_FILE = 'iosxe_config.txt'
    LITERAL_CLI_STRING = 'ios-config'
    # CSR1000v doesn't 'officially' support E1000, but it mostly works
    SUPPORTED_NIC_TYPES = ["E1000", "virtio", "VMXNET3"]

    # CSR1000V supports 1, 2, 4, or 8 CPUs.
    CPU_MAX = 8
    # Minimum 2.5 GiB, max 8 GiB.
    RAM_MIN = 2560
    RAM_MAX = 8192
    # CSR1000V requires 3 NICs and supports up to 26.
    NIC_MIN = 3
    NIC_MAX = 26
    # CSR1000V supports 0-2 serial ports.
    SER_MAX = 2

    @classmethod
    def controller_type_for_device(cls, device_type):
        """CSR1000V uses SCSI for hard disks and IDE for CD-ROMs.

        :param str device_type: 'harddisk' or 'cdrom'
        :return: 'ide' for CD-ROM, 'scsi' for hard disk
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

        :param int nic_number: Nth NIC to name.
        :return:
          * "GigabitEthernet1"
          * "GigabitEthernet2"
          * etc.
        """
        return "GigabitEthernet" + str(nic_number)

    @classmethod
    def validate_cpu_count(cls, cpus):
        """CSR1000V supports 1, 2, 4, or 8 CPUs.

        :param int cpus: Number of CPUs.
        :raises ValueTooLowError: if ``cpus`` is less than :const:`CPU_MIN`
        :raises ValueTooHighError: if ``cpus`` is more than :const:`CPU_MAX`
        :raises ValueUnsupportedError: if ``cpus`` is an unsupported value
          between :const:`CPU_MIN` and :const:`CPU_MAX`
        """
        validate_int(cpus, 1, 8, "CPUs")
        if cpus not in [1, 2, 4, 8]:
            raise ValueUnsupportedError("CPUs", cpus, [1, 2, 4, 8])


class IOSv(GenericPlatform):
    """Platform-specific logic for Cisco IOSv."""

    PLATFORM_NAME = "Cisco IOSv"

    CONFIG_TEXT_FILE = 'ios_config.txt'
    LITERAL_CLI_STRING = None
    # IOSv has no CD-ROM driver so bootstrap configs must be provided on disk.
    BOOTSTRAP_DISK_TYPE = 'harddisk'
    SUPPORTED_NIC_TYPES = ["E1000"]

    # IOSv only supports a single CPU.
    CPU_MAX = 1
    # IOSv supports up to 16 NICs.
    NIC_MAX = 16
    # IOSv requires 1-2 serial ports.
    SER_MIN = 1
    SER_MAX = 2

    @classmethod
    def guess_nic_name(cls, nic_number):
        """GigabitEthernet0/0, GigabitEthernet0/1, etc.

        :param int nic_number: Nth NIC to name.
        :return:
          * "GigabitEthernet0/0"
          * "GigabitEthernet0/1"
          * etc.
        """
        return "GigabitEthernet0/" + str(nic_number - 1)

    @classmethod
    def validate_memory_amount(cls, mebibytes):
        """IOSv has minimum 192 MiB (with minimal feature set), max 3 GiB.

        :param int mebibytes: RAM amount, in MiB.
        :raises ValueTooLowError: if :attr:`mebibytes` is less than
          :const:`RAM_MIN`
        :raises ValueTooHighError: if :attr:`mebibytes` is more than
          :const:`RAM_MAX`
        """
        if mebibytes < 192:
            raise ValueTooLowError("RAM", str(mebibytes) + " MiB", "192 MiB")
        elif mebibytes < 384:
            # Warn but allow
            logger.warning("Less than 384MiB of RAM may not be sufficient "
                           "for some IOSv feature sets")
        elif mebibytes > 3072:
            raise ValueTooHighError("RAM", str(mebibytes) + " MiB", "3 GiB")


class NXOSv(GenericPlatform):
    """Platform-specific logic for Cisco NX-OSv (Titanium)."""

    PLATFORM_NAME = "Cisco NX-OSv"

    CONFIG_TEXT_FILE = 'nxos_config.txt'
    LITERAL_CLI_STRING = None
    SUPPORTED_NIC_TYPES = ["E1000", "virtio"]

    # NX-OSv requires 1-8 CPUs.
    CPU_MAX = 8
    # NX-OSv requires 2-8 GiB of RAM.
    RAM_MIN = 2048
    RAM_MAX = 8192
    # NX-OSv requires 1-2 serial ports.
    SER_MIN = 1
    SER_MAX = 2

    @classmethod
    def guess_nic_name(cls, nic_number):
        """NX-OSv names its NICs a bit interestingly...

        :param int nic_number: Nth NIC to name.
        :return:
          * "mgmt0"
          * "Ethernet2/1"
          * "Ethernet2/2"
          * ...
          * "Ethernet2/48"
          * "Ethernet3/1"
          * "Ethernet3/2"
          * ...
        """
        if nic_number == 1:
            return "mgmt0"
        else:
            return ("Ethernet{0}/{1}".format((nic_number - 2) // 48 + 2,
                                             (nic_number - 2) % 48 + 1))


PRODUCT_PLATFORM_MAP = {
    'com.cisco.csr1000v':    CSR1000V,
    'com.cisco.iosv':        IOSv,
    'com.cisco.nx-osv':      NXOSv,
    'com.cisco.ios-xrv':     IOSXRv,
    'com.cisco.ios-xrv.rp':  IOSXRvRP,
    'com.cisco.ios-xrv.lc':  IOSXRvLC,
    'com.cisco.ios-xrv9000': IOSXRv9000,
    # Some early releases of IOS XRv 9000 used the
    # incorrect string 'com.cisco.ios-xrv64'.
    'com.cisco.ios-xrv64':   IOSXRv9000,
}
"""Mapping of known product class strings to Platform classes."""
