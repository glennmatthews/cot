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

"""API and generic implementation of platform-specific logic."""

import logging
from collections import defaultdict
from enum import Enum

from COT.data_validation import (
    validate_int, ValueUnsupportedError, NIC_TYPES, ValidRange,
)

logger = logging.getLogger(__name__)


class Hardware(Enum):
    """Enumeration of hardware types that have integer quantities."""

    # The actual numbers don't matter at all
    cpus = 1
    memory = 2
    nic_count = 3
    serial_count = 4


class Platform(object):
    """Generic class for operations that depend on guest platform.

    To be used whenever the guest is unrecognized or does not need
    special handling.
    """

    PLATFORM_NAME = "(unrecognized platform, generic)"
    """String used as a descriptive label for this class of Platform."""

    CONFIG_TEXT_FILE = 'config.txt'
    """When embedding a primary configuration text file, use this filename.

    .. seealso::
        :attr:`COT.inject_config.COTInjectConfig.config_file`
    """

    SECONDARY_CONFIG_TEXT_FILE = None
    """When embedding a secondary configuration text file, use this filename.

    Most platforms do not support a secondary configuration file.

    .. seealso::
        :attr:`COT.inject_config.COTInjectConfig.secondary_config_file`
    """

    LITERAL_CLI_STRING = 'config'
    """Key prefix for converting text config to OVF environment properties.

    Most platforms do not support configuration properties in the environment,
    and so should define this attribute to ``None``.

    .. seealso::
        :meth:`~COT.vm_description.VMDescription.config_file_to_properties`
    """

    BOOTSTRAP_DISK_TYPE = 'cdrom'
    """Type of disk (cdrom/harddisk) to use for bootstrap configuration.

    Most platforms use a CD-ROM for this purpose.
    """

    SUPPORTED_NIC_TYPES = NIC_TYPES
    """List of NIC device types supported by this platform."""

    PRODUCT_PLATFORM_MAP = {}
    """Mapping of product strings to product classes."""

    HARDWARE_LIMITS = {
        Hardware.cpus: ValidRange(1, None),
        Hardware.memory: ValidRange(1, None),
        Hardware.nic_count: ValidRange(0, None),
        Hardware.serial_count: ValidRange(0, None),
    }
    """Range of valid values for various hardware properties."""

    @classmethod
    def for_product_string(cls, product_string):
        """Get the class of Platform corresponding to a product string.

        Args:
          product_string (str): String such as 'com.cisco.iosxrv'

        Returns:
          Platform: Instance of Platform or the appropriate subclass.

        Examples:
          ::

            >>> Platform.for_product_string("com.cisco.n9k")
            <class 'COT.platforms.cisco_nexus_9000v.Nexus9000v'>
            >>> Platform.for_product_string(None)
            <class 'COT.platforms.platform.Platform'>
            >>> Platform.for_product_string("frobozz")
            <class 'COT.platforms.platform.Platform'>
        """
        if product_string is None:
            logger.notice("No product class given. Treating this as"
                          " a generic platform.")
            return Platform()
        if product_string in cls.PRODUCT_PLATFORM_MAP:
            return cls.PRODUCT_PLATFORM_MAP[product_string]()
        logger.notice("Unrecognized product class '%s'. Treating this as"
                      " a generic platform.", product_string)
        logger.verbose("Known product classes are %s",
                       cls.PRODUCT_PLATFORM_MAP.keys())
        return Platform()

    def __init__(self):
        """Create an instance of this class."""
        self._already_validated = defaultdict(dict)
        """Cache of values already validated.

        ::

          _already_validated[Hardware.cpus][value] = True

        Used to avoid raising the same ValueError over and over from various
        points in the code.
        """

    def __str__(self):
        """String representation - same as :attr:`PLATFORM_NAME`."""
        return self.__class__.PLATFORM_NAME

    # Some of these methods are semi-abstract, so:
    # pylint: disable=unused-argument, no-self-use

    def controller_type_for_device(self, device_type):
        """Get the default controller type for the given device type.

        Args:
          device_type (str): 'harddisk', 'cdrom', etc.

        Returns:
          str: 'ide' unless overridden by subclass.
        """
        # For most platforms IDE is the correct default.
        return 'ide'

    def guess_nic_name(self, nic_number):
        """Guess the name of the Nth NIC for this platform.

        .. note:: This method counts from 1, not from 0!

        Args:
          nic_number (int): Nth NIC to name.

        Returns:
          str: "Ethernet1", "Ethernet2", etc. unless overridden by subclass.
        """
        return "Ethernet" + str(nic_number)

    def validate_cpu_count(self, cpus):
        """Throw an error if the number of CPUs is not a supported value.

        Args:
          cpus (int): Number of CPUs

        Raises:
          ValueTooLowError: if ``cpus`` is less than the minimum required
              by this platform
          ValueTooHighError: if ``cpus`` exceeds the maximum supported
              by this platform
        """
        if cpus not in self._already_validated[Hardware.cpus]:
            self._already_validated[Hardware.cpus][cpus] = True
            validate_int(cpus, *self.HARDWARE_LIMITS[Hardware.cpus],
                         label="CPUs for platform {0}".format(self))

    def validate_memory_amount(self, mebibytes):
        """Throw an error if the amount of RAM is not supported.

        Args:
          mebibytes (int): RAM, in MiB.

        Raises:
          ValueTooLowError: if ``mebibytes`` is less than the minimum
              required by this platform
            ValueTooHighError: if ``mebibytes`` is more than the maximum
                supported by this platform
        """
        if mebibytes not in self._already_validated[Hardware.memory]:
            self._already_validated[Hardware.memory][mebibytes] = True
            validate_int(mebibytes, *self.HARDWARE_LIMITS[Hardware.memory],
                         label="MiB of RAM for platform {0}".format(self))

    def validate_nic_count(self, count):
        """Throw an error if the number of NICs is not supported.

        Args:
          count (int): Number of NICs.

        Raises:
          ValueTooLowError: if ``count`` is less than the minimum
              required by this platform
          ValueTooHighError: if ``count`` is more than the maximum
              supported by this platform
        """
        if count not in self._already_validated[Hardware.nic_count]:
            self._already_validated[Hardware.nic_count][count] = True
            validate_int(count, *self.HARDWARE_LIMITS[Hardware.nic_count],
                         label="NIC count for platform {0}".format(self))

    def validate_nic_type(self, type_string):
        """Throw an error if the NIC type string is not supported.

        .. seealso::
           - :func:`COT.data_validation.canonicalize_nic_subtype`
           - :data:`COT.data_validation.NIC_TYPES`

        Args:
          type_string (str): See :data:`COT.data_validation.NIC_TYPES`

        Raises:
          ValueUnsupportedError: if ``type_string`` is not in
              :const:`SUPPORTED_NIC_TYPES`
        """
        if type_string not in self.SUPPORTED_NIC_TYPES:
            raise ValueUnsupportedError(
                "NIC type for {0}".format(self),
                type_string, self.SUPPORTED_NIC_TYPES)

    def validate_nic_types(self, type_list):
        """Throw an error if any NIC type string in the list is unsupported.

        Args:
          type_list (list): See :data:`COT.data_validation.NIC_TYPES`

        Raises:
          ValueUnsupportedError: if any value in ``type_list`` is not in
              :const:`SUPPORTED_NIC_TYPES`
        """
        for type_string in type_list:
            self.validate_nic_type(type_string)

    def validate_serial_count(self, count):
        """Throw an error if the number of serial ports is not supported.

        Args:
          count (int): Number of serial ports.

        Raises:
          ValueTooLowError: if ``count`` is less than the minimum
              required by this platform
          ValueTooHighError: if ``count`` is more than the maximum
              supported by this platform
        """
        if count not in self._already_validated[Hardware.serial_count]:
            self._already_validated[Hardware.serial_count][count] = True
            validate_int(count, *self.HARDWARE_LIMITS[Hardware.serial_count],
                         label="serial port count for platform {0}"
                         .format(self))


Platform.PRODUCT_PLATFORM_MAP[None] = Platform
