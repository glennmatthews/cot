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

"""API and generic implementation of platform-specific logic."""

from COT.data_validation import validate_int, ValueUnsupportedError, NIC_TYPES


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

    @classmethod
    def controller_type_for_device(cls, _device_type):
        """Get the default controller type for the given device type."""
        # For most platforms IDE is the correct default.
        return 'ide'

    @classmethod
    def guess_nic_name(cls, nic_number):
        """Guess the name of the Nth NIC for this platform.

        .. note:: This method counts from 1, not from 0!
        """
        return "Ethernet" + str(nic_number)

    @classmethod
    def validate_cpu_count(cls, cpus):
        """Throw an error if the number of CPUs is not a supported value."""
        validate_int(cpus, 1, None, "CPUs")

    @classmethod
    def validate_memory_amount(cls, mebibytes):
        """Throw an error if the amount of RAM is not supported."""
        validate_int(mebibytes, 1, None, "RAM")

    @classmethod
    def validate_nic_count(cls, count):
        """Throw an error if the number of NICs is not supported."""
        validate_int(count, 0, None, "NIC count")

    @classmethod
    def validate_nic_type(cls, type_string):
        """Throw an error if the NIC type string is not supported.

        .. seealso::
           - :func:`COT.data_validation.canonicalize_nic_subtype`
           - :data:`COT.data_validation.NIC_TYPES`
        """
        if type_string not in cls.SUPPORTED_NIC_TYPES:
            raise ValueUnsupportedError("NIC type", type_string,
                                        cls.SUPPORTED_NIC_TYPES)

    @classmethod
    def validate_nic_types(cls, type_list):
        """Throw an error if any NIC type string in the list is unsupported."""
        for type_string in type_list:
            cls.validate_nic_type(type_string)

    @classmethod
    def validate_serial_count(cls, count):
        """Throw an error if the number of serial ports is not supported."""
        validate_int(count, 0, None, "serial port count")
