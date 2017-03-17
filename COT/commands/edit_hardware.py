#!/usr/bin/env python
#
# edit_hardware.py - Implements "edit-hardware" sub-command
#
# September 2013, Glenn F. Matthews
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

"""Module for editing hardware details of a VM.

**Functions**

.. autosummary::
  :nosignatures:

  expand_list_wildcard
  guess_list_wildcard

**Classes**

.. autosummary::
  :nosignatures:

  COTEditHardware
"""

import argparse
import logging
import re
import textwrap
import warnings

from COT.data_validation import (
    alphanum_split,
    canonicalize_ide_subtype,
    canonicalize_nic_subtype,
    canonicalize_scsi_subtype,
    no_whitespace, mac_address, non_negative_int, positive_int,
    InvalidInputError,
)
from .command import command_classes, ReadWriteCommand

logger = logging.getLogger(__name__)


class COTEditHardware(ReadWriteCommand):
    """Edit hardware information (CPUs, RAM, NICs, etc.).

    Inherited attributes:
    :attr:`~Command.ui`,
    :attr:`~ReadWriteCommand.package`,
    :attr:`~ReadWriteCommand.output`

    Attributes:
    :attr:`profiles`,
    :attr:`delete_all_other_profiles`,
    :attr:`cpus`,
    :attr:`memory`,
    :attr:`nics`,
    :attr:`nic_types`,
    :attr:`mac_addresses_list`,
    :attr:`nic_networks`,
    :attr:`nic_names`,
    :attr:`network_descriptions`,
    :attr:`serial_ports`,
    :attr:`serial_connectivity`,
    :attr:`scsi_subtypes`,
    :attr:`ide_subtypes`,
    :attr:`virtual_system_type`
    """

    def __init__(self, ui):
        """Instantiate this command with the given UI.

        Args:
          ui (UI): User interface instance.
        """
        super(COTEditHardware, self).__init__(ui)
        self.profiles = None
        """Configuration profile(s) to edit."""
        self.delete_all_other_profiles = False
        """Delete all profiles other than those set in :attr:`profiles`."""
        self._cpus = None
        self._memory = None
        self._nics = None
        self._nic_types = None
        self.mac_addresses_list = None
        """List of MAC addresses to set."""
        self.nic_networks = None
        """List of NIC-to-network mappings.

        Can use wildcards as described in :func:`expand_list_wildcard`.
        """
        self.nic_names = None
        """List of NIC name strings.

        Can use wildcards as described in :func:`expand_list_wildcard`.
        """
        self.network_descriptions = None
        """List of network description strings.

        Can use wildcards as described in :func:`expand_list_wildcard`.
        """
        self._serial_ports = None
        self.serial_connectivity = None
        """List of serial connection strings."""
        self._scsi_subtypes = None
        self._ide_subtypes = None
        self.virtual_system_type = None
        """Virtual system type"""

    @property
    def cpus(self):
        """Number of CPUs to set."""
        return self._cpus

    @cpus.setter
    def cpus(self, value):
        try:
            value = int(value)
        except ValueError:
            raise InvalidInputError("cpus value must be an integer")
        if value < 1:
            raise InvalidInputError("CPU count must be at least 1")
        self.ui.validate_value(self.vm.platform.validate_cpu_count, value)
        self._cpus = value

    @property
    def memory(self):
        """Amount of RAM (in megabytes) to set."""
        return self._memory

    # We like to see memory input in the form "4096M" or "4 GB" or "2 GiB"
    MEMORY_REGEXP = r"^\s*(\d+)\s*([mMgG])?i?[bB]?\s*$"

    @memory.setter
    def memory(self, value):
        value = str(value)
        match = re.match(self.MEMORY_REGEXP, value)
        if not match:
            raise InvalidInputError("Could not parse memory string '{0}'"
                                    .format(value))
        mem_value = int(match.group(1))
        if mem_value <= 0:
            raise InvalidInputError("Memory must be greater than zero")
        if match.group(2) == 'M' or match.group(2) == 'm':
            # default
            logger.debug("Memory specified in megabytes")
        elif match.group(2) == 'G' or match.group(2) == 'g':
            logger.debug("Memory specified in gigabytes - "
                         "converting to megabytes")
            mem_value *= 1024
        else:
            # Try to be clever and guess the units
            if mem_value <= 64:
                logger.warning("Memory units not specified, "
                               "guessing '%s' means '%s GiB'",
                               mem_value, mem_value)
                mem_value *= 1024
            else:
                logger.warning("Memory units not specified, "
                               "guessing '%s' means '%s MiB'",
                               mem_value, mem_value)
        self.ui.validate_value(self.vm.platform.validate_memory_amount,
                               mem_value)
        self._memory = mem_value

    @property
    def nics(self):
        """Number of NICs to set."""
        return self._nics

    @nics.setter
    def nics(self, value):
        try:
            value = int(value)
        except ValueError:
            raise InvalidInputError("nics value must be an integer")
        non_negative_int(value, label="nics")
        self.ui.validate_value(self.vm.platform.validate_nic_count, value)
        self._nics = value

    @property
    def nic_type(self):
        """NIC type string to set.

        .. deprecated:: 1.5
           Use :attr:`nic_types` instead.
        """
        warnings.warn("Use nic_types instead", DeprecationWarning)
        if self.nic_types is None or len(self.nic_types) == 0:
            return None
        if len(self.nic_types) > 1:
            raise TypeError("nic_types has more than one element ({0}). "
                            "Use nic_types instead of nic_type."
                            .format(self.nic_types))
        return self.nic_types[0]

    @nic_type.setter
    def nic_type(self, value):
        warnings.warn("Use nic_types instead", DeprecationWarning)
        self.nic_types = [value]

    @property
    def nic_types(self):
        """List of NIC type strings to set."""
        return self._nic_types

    @nic_types.setter
    def nic_types(self, value):
        value = [canonicalize_nic_subtype(v) for v in value]
        self.ui.validate_value(self.vm.platform.validate_nic_types, value)
        self._nic_types = value

    @property
    def serial_ports(self):
        """Serial port count to set."""
        return self._serial_ports

    @serial_ports.setter
    def serial_ports(self, value):
        try:
            value = int(value)
        except ValueError:
            raise InvalidInputError("serial_ports value must be an integer")
        non_negative_int(value, label="serial_ports")
        self.ui.validate_value(self.vm.platform.validate_serial_count, value)
        self._serial_ports = value

    @property
    def scsi_subtype(self):
        """SCSI controller subtype string to set.

        .. deprecated:: 1.5
           Use :attr:`scsi_subtypes` instead.
        """
        warnings.warn("Use scsi_subtypes instead", DeprecationWarning)
        if self.scsi_subtypes is None or len(self.scsi_subtypes) == 0:
            return None
        if len(self.scsi_subtypes) > 1:
            raise TypeError("scsi_subtypes has more than one element ({0}). "
                            "Use scsi_subtypes instead of scsi_subtype."
                            .format(self.scsi_subtypes))
        return self.scsi_subtypes[0]

    @scsi_subtype.setter
    def scsi_subtype(self, value):
        warnings.warn("Use scsi_subtypes instead", DeprecationWarning)
        self.scsi_subtypes = [value]

    @property
    def scsi_subtypes(self):
        """SCSI controller subtype string(s) to set."""
        return self._scsi_subtypes

    @scsi_subtypes.setter
    def scsi_subtypes(self, value):
        value = [canonicalize_scsi_subtype(v) for v in value]
        value = [v for v in value if v]
        # TODO: self.vm.platform.validate_scsi_types(value)
        self._scsi_subtypes = value

    @property
    def ide_subtype(self):
        """IDE controller subtype string to set.

        .. deprecated:: 1.5
           Use :attr:`ide_subtypes` instead.
        """
        warnings.warn("Use ide_subtypes instead", DeprecationWarning)
        if self.ide_subtypes is None or len(self.ide_subtypes) == 0:
            return None
        if len(self.ide_subtypes) > 1:
            raise TypeError("ide_subtypes has more than one element ({0}). "
                            "Use ide_subtypes instead of ide_subtype."
                            .format(self.ide_subtypes))
        return self.ide_subtypes[0]

    @ide_subtype.setter
    def ide_subtype(self, value):
        warnings.warn("Use ide_subtypes instead", DeprecationWarning)
        self.ide_subtypes = [value]

    @property
    def ide_subtypes(self):
        """IDE controller subtype string(s) to set."""
        return self._ide_subtypes

    @ide_subtypes.setter
    def ide_subtypes(self, value):
        value = [canonicalize_ide_subtype(v) for v in value]
        value = [v for v in value if v]
        # TODO: self.vm.platform.validate_ide_types(value)
        self._ide_subtypes = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        Returns:
          tuple: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        # Need some work to do!
        if not any([x is not None and x is not False for x in [
                self.profiles,
                self.delete_all_other_profiles,
                self.cpus,
                self.memory,
                self.nics,
                self.nic_types,
                self.mac_addresses_list,
                self.nic_networks,
                self.nic_names,
                self.network_descriptions,
                self.serial_ports,
                self.serial_connectivity,
                self.scsi_subtypes,
                self.ide_subtypes,
                self.virtual_system_type,
        ]]):
            return (False, "No work requested! Please specify at least "
                    "one hardware change")
        return super(COTEditHardware, self).ready_to_run()

    def _run_create_new_profiles(self):
        """Create new profiles as needed, with user input.

        Helper for :meth:`_run_update_profiles`.
        """
        # Create new profiles as needed
        profile_list = self.vm.config_profiles
        for profile in self.profiles:  # pylint: disable=not-an-iterable
            if profile not in profile_list:
                self.ui.confirm_or_die(
                    "Profile '{0}' does not exist. Create it?"
                    .format(profile))
                label = self.ui.get_input(
                    "Please enter a label for this configuration profile",
                    profile)
                desc = self.ui.get_input(
                    "Please enter a description for this "
                    "configuration profile", label)
                self.vm.create_configuration_profile(profile, label=label,
                                                     description=desc)

    def _run_delete_other_profiles(self):
        """Delete all profiles except those requested.

        Helper for :meth:`_run_update_profiles`.
        """
        if self.profiles is None:
            self.ui.confirm_or_die(
                "--delete-all-other-profiles was specified but no "
                "--profiles was specified. Really proceed to delete ALL "
                "configuration profiles?")
            profiles_to_delete = self.vm.config_profiles
        else:
            profiles_to_delete = list(set(self.vm.config_profiles) -
                                      set(self.profiles))
        for profile in profiles_to_delete:
            if self.profiles is not None:
                if not self.ui.confirm("Delete profile {0}?".format(profile)):
                    logger.verbose("Skipping deletion of profile %s", profile)
                    continue
            # else (profiles == None) we already confirmed earlier
            self.vm.delete_configuration_profile(profile)

    def _run_update_profiles(self):
        """Handle profile changes. Helper for :meth:`run`."""
        if self.profiles is not None:
            # Warn user about non-profile-aware properties
            if self.virtual_system_type is not None:
                self.ui.confirm_or_die(
                    "VirtualSystemType is not filtered by configuration"
                    " profile. Requested system type(s) '{0}' will be set for"
                    " ALL profiles, not just profile(s) {1}. Continue?"
                    .format(" ".join(self.virtual_system_type), self.profiles))
            if self.network_descriptions is not None:
                self.ui.confirm_or_die(
                    "Network descriptions are not filtered by configuration"
                    " profile. Requested network descriptions will be set for"
                    " networks across ALL profiles, not just profile(s) {0}."
                    " Continue?".format(self.profiles))

            self._run_create_new_profiles()

        if self.delete_all_other_profiles:
            self._run_delete_other_profiles()

    def _run_infer_networks_from_nics(self):
        """Infer network information if needed when creating NICs.

        Helper for :meth:`run`.
        """
        if self.nics is None or self.nic_networks is not None:
            return

        # If we're not creating new NICs, nothing needed
        # If we don't have at least 2 existing NICs, not enough info to infer
        current_nic_count = max(self.vm.get_nic_count(self.profiles).values())
        if self.nics <= current_nic_count or current_nic_count < 2:
            return

        # Only try to infer if there are the same number of NICs and networks
        # TODO: this is a bit overly conservative - if we had an API for
        #       retrieving the NIC-to-network mapping list, we could dispense
        #       with this check and work on the mapping list instead.
        current_network_count = len(self.vm.networks)
        if current_nic_count != current_network_count:
            return

        # TODO: the below relies on the assumption that the networks list
        #       is in the same order as the NICs list, which is not a given.

        logger.notice("Given that all existing NICs are mapped to unique "
                      "networks, trying to guess an implicit pattern for "
                      "creating new networks.")
        # Can we guess a pattern from vm.networks?
        self.nic_networks = guess_list_wildcard(self.vm.networks)
        if self.nic_networks:
            logger.info('Identified a pattern: --nic-networks "%s"',
                        '" "'.join(self.nic_networks))
        else:
            logger.info("No pattern could be identified from existing "
                        "network names %s", self.vm.networks)

        # If the user didn't specify the network descriptions, let's
        # see if we can guess that too...
        if self.network_descriptions is None:
            self.network_descriptions = guess_list_wildcard(
                self.vm.network_descriptions)
            if self.network_descriptions:
                logger.info("Identified a pattern: "
                            '--network-descriptions "%s"',
                            '" "'.join(self.network_descriptions))
            else:
                logger.info("No pattern could be identified from "
                            "existing network descriptions %s",
                            self.vm.network_descriptions)

    def _run_update_nics(self):
        """Handle NIC changes. Helper for :meth:`run`."""
        vm = self.vm

        nics_dict = vm.get_nic_count(self.profiles)
        if self.nics is not None:
            for (profile, count) in nics_dict.items():
                if self.nics < count:
                    self.ui.confirm_or_die(
                        "Profile {0} currently has {1} NIC(s). "
                        "Delete {2} NIC(s) to reduce to {3} total?"
                        .format(profile, count,
                                (count - self.nics), self.nics))
            vm.set_nic_count(self.nics, self.profiles)

        if self.nic_types is not None:
            vm.set_nic_types(self.nic_types, self.profiles)

        if self.mac_addresses_list is not None:
            vm.set_nic_mac_addresses(self.mac_addresses_list, self.profiles)

    def _run_update_networks(self):
        """Handle network changes. Helper for :meth:`run`."""
        vm = self.vm
        nics_dict = vm.get_nic_count(self.profiles)
        max_nics = max(nics_dict.values())
        existing_networks = vm.networks

        # Special case:
        # If we added NICs in _run_update_nics to an OVF previously with none,
        # we MUST create a network, as NICs with no Connection are not valid.
        if max_nics > 0 and not existing_networks:
            if self.nic_networks is None:
                self.nic_networks = ['VM Network']
                logger.warning("No network names specified, but NICs must be "
                               "mapped to a network. Will add network '%s'.",
                               self.nic_networks[0])

        new_descs = expand_list_wildcard(self.network_descriptions,
                                         max_nics)
        if self.nic_networks is None and self.network_descriptions is not None:
            # Just rename existing networks, instead of making new ones
            for network, desc in zip(vm.networks, new_descs):
                # Despite the name, create_network can also be used to
                # update an existing network.
                vm.create_network(network, desc)
            return

        if self.nic_networks is not None:
            new_networks = expand_list_wildcard(self.nic_networks, max_nics)
            for network in new_networks:
                if new_descs:
                    new_desc = new_descs.pop(0)
                else:
                    new_desc = None

                if network not in existing_networks:
                    self.ui.confirm_or_die(
                        "Network {0} is not currently defined. "
                        "Create it?".format(network))
                    if not new_desc:
                        new_desc = self.ui.get_input(
                            "Please enter a description for this network",
                            network)
                # create or update
                vm.create_network(network, new_desc)

            vm.set_nic_networks(new_networks, self.profiles)

    def _run_update_nic_names(self):
        """Update NIC names. Helper for :meth:`run`."""
        if self.nic_names is not None:
            vm = self.vm
            nics_dict = vm.get_nic_count(self.profiles)
            max_nics = max(nics_dict.values())
            names = expand_list_wildcard(self.nic_names, max_nics)
            vm.set_nic_names(names, self.profiles)

    def _run_update_serial(self):
        """Handle serial port changes. Helper for :meth:`run`."""
        if self.serial_ports is not None:
            serial_dict = self.vm.get_serial_count(self.profiles)
            for (profile, count) in serial_dict.items():
                if self.serial_ports < count:
                    self.ui.confirm_or_die(
                        "Profile {0} currently has {1} serial port(s). "
                        "Delete {2} port(s) to reduce to {3} total?"
                        .format(profile, count, (count - self.serial_ports),
                                self.serial_ports))
            self.vm.set_serial_count(self.serial_ports, self.profiles)

        if self.serial_connectivity is not None:
            serial_dict = self.vm.get_serial_count(self.profiles)
            for (profile, count) in serial_dict.items():
                if len(self.serial_connectivity) < count:
                    self.ui.confirm_or_die(
                        "There are {0} serial port(s) under profile {1}, but "
                        "you have specified connectivity information for only "
                        "{2}. "
                        "\nThe remaining ports will be unreachable. Continue?"
                        .format(count, profile,
                                len(self.serial_connectivity)))
            self.vm.set_serial_connectivity(self.serial_connectivity,
                                            self.profiles)

    def run(self):
        """Do the actual work of this command.

        Raises:
          InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTEditHardware, self).run()

        self._run_update_profiles()

        vm = self.vm

        if self.virtual_system_type is not None:
            vm.system_types = self.virtual_system_type

        if self.cpus is not None:
            vm.set_cpu_count(self.cpus, self.profiles)

        if self.memory is not None:
            vm.set_memory(self.memory, self.profiles)

        self._run_infer_networks_from_nics()

        self._run_update_nics()

        self._run_update_networks()

        # Update NIC names *after* updating networks, as we don't want
        # network-induced name changes to overwrite user-specified names.
        self._run_update_nic_names()

        self._run_update_serial()

        if self.scsi_subtypes is not None:
            vm.set_scsi_subtypes(self.scsi_subtypes, self.profiles)

        if self.ide_subtypes is not None:
            vm.set_ide_subtypes(self.ide_subtypes, self.profiles)

    def create_subparser(self):
        """Create 'edit-hardware' CLI subparser."""
        wrapper = textwrap.TextWrapper(width=self.ui.terminal_width - 1,
                                       initial_indent='  ',
                                       subsequent_indent='  ')
        parser = self.ui.add_subparser(
            'edit-hardware',
            add_help=False,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=self.ui.fill_usage("edit-hardware", [
                "PACKAGE [-o OUTPUT] -v TYPE [TYPE2 ...]",
                "PACKAGE [-o OUTPUT] \
[-p PROFILE [PROFILE2 ...] [--delete-all-other-profiles]] [-c CPUS] \
[-m MEMORY] [-n NICS] [--nic-types TYPE [TYPE2 ...]] \
[-N NETWORK [NETWORK2 ...]] [-M MAC1 [MAC2 ...]] \
[--nic-names NAME1 [NAME2 ...]] [-s SERIAL_PORTS] [-S URI1 [URI2 ...]] \
[--scsi-subtypes TYPE [TYPE2 ...]] [--ide-subtypes TYPE [TYPE2 ...]]",
            ]),
            help="Edit virtual machine hardware properties of an OVF",
            description="Edit hardware properties of the specified OVF or OVA",
            epilog=("Notes:\n" + wrapper.fill(
                "The --nic-names, --nic-networks, and --network-descriptions"
                " options support the use of a wildcard value to"
                " automatically generate a series of consecutively numbered"
                " strings. The syntax for the wildcard option is '{' followed"
                " by a number to start incrementing from, followed by '}'."
                " See examples below."
            ) + "\n\n" + self.ui.fill_examples([
                ('Create a new profile named "1CPU-8GB" with 1 CPU and 8'
                 ' gigabytes of RAM',
                 'cot edit-hardware csr1000v.ova --output csr1000v_custom.ova'
                 ' --profile 1CPU-4GB --cpus 1 --memory 8GB'),
                ("Wildcard example - without caring about how many NICs are"
                 " defined in the input OVA, rename all of the NICs in the"
                 " output OVA as 'Ethernet0/10', 'Ethernet0/11',"
                 " 'Ethernet0/12', etc., and map them to networks"
                 " 'Ethernet0_10', 'Ethernet0_11', 'Ethernet0_12', etc.,"
                 " which are described as 'Data network 1', 'Data network 2',"
                 " etc.",
                 'cot edit-hardware input.ova -o output.ova'
                 ' --nic-names "Ethernet0/{10}"'
                 ' --nic-networks "Ethernet0_{10}"'
                 ' --network-descriptions "Data network {1}"'),
                ("Combination of fixed and wildcarded names - rename the NICs"
                 " in the output OVA as 'mgmt', 'eth0', 'eth1', 'eth2'...",
                 'cot edit-hardware input.ova -o output.ova'
                 ' --nic-names "mgmt" "eth{0}"'),
            ])))

        group = parser.add_argument_group("general options")

        group.add_argument('-h', '--help', action='help',
                           help="Show this help message and exit")
        group.add_argument('-o', '--output',
                           help="Name/path of new OVF/OVA package to create "
                           "instead of updating the existing OVF")
        group.add_argument('-v', '--virtual-system-type',
                           action='append', nargs='+',
                           type=no_whitespace, metavar=('TYPE', 'TYPE2'),
                           help="Change virtual system type(s) supported by "
                           "this OVF/OVA package.")
        group.add_argument('-p', '--profiles', action='append', nargs='+',
                           type=no_whitespace, metavar=('PROFILE', 'PROFILE2'),
                           help="Make hardware changes only under the given "
                           "configuration profile(s). (default: changes apply "
                           "to all profiles)")
        group.add_argument('--delete-all-other-profiles', action='store_true',
                           help="Delete all configuration profiles other than"
                           " those specified with the --profiles option")

        group = parser.add_argument_group("computational hardware options")

        group.add_argument('-c', '--cpus', type=positive_int,
                           help="Set the number of CPUs.")
        group.add_argument('-m', '--memory',
                           help="Set the amount of RAM. "
                           '(Examples: "4096M", "4 GiB")')

        group = parser.add_argument_group("network interface options")

        group.add_argument('-n', '--nics', type=non_negative_int,
                           help="Set the number of NICs.")
        group.add_argument('--nic-types', action='append', nargs='+',
                           metavar=('TYPE', 'TYPE2'),
                           help="Set the hardware type(s) for all NICs. "
                           "(default: do not change existing NICs, and new "
                           "NICs added will match the existing type(s).)")
        group.add_argument('--nic-names', action='append', nargs='+',
                           metavar=('NAME1', 'NAME2'),
                           help="Specify a list of one or more NIC names or "
                           "patterns to apply to NIC devices. See Notes.")
        group.add_argument(
            '-N', '--nic-networks', action='append', nargs='+',
            metavar=('NETWORK', 'NETWORK2'),
            help="Specify a series of one or more network names or patterns"
            " to map NICs to. See Notes.")
        group.add_argument(
            '--network-descriptions', action='append', nargs='+',
            metavar=('NAME1', 'NAME2'),
            help="Specify a list of one or more network descriptions or"
                 " patterns to apply to the networks. See Notes.")
        group.add_argument(
            '-M', '--mac-addresses-list', type=mac_address,
            metavar=('MAC1', 'MAC2'), action='append', nargs='+',
            help="Specify a list of MAC addresses for the NICs. "
            "If N MACs are specified, the first (N-1) NICs will receive the"
            " first (N-1) MACs, and all remaining NICs will use the Nth MAC")

        group = parser.add_argument_group("serial port options")

        group.add_argument('-s', '--serial-ports', type=non_negative_int,
                           help="Set the number of serial ports.")
        group.add_argument(
            '-S', '--serial-connectivity',
            metavar=('URI1', 'URI2'), action='append', nargs='+',
            help="Specify a series of connectivity strings (URIs such as"
            ' "telnet://localhost:9101") to map serial ports to. If fewer'
            " URIs than serial ports are specified, the remaining ports"
            " will be unmapped.")

        group = parser.add_argument_group("disk and disk controller options")

        group.add_argument(
            '--scsi-subtypes', action='append', nargs='+',
            metavar=('TYPE', 'TYPE2'),
            help='Set resource subtype(s) (such as "lsilogic" or "virtio")'
            " for all SCSI controllers. If an empty string is provided,"
            " any existing subtype will be removed.")
        group.add_argument(
            '--ide-subtypes', action='append', nargs='+',
            metavar=('TYPE', 'TYPE2'),
            help='Set resource subtype(s) (such as "virtio") for all IDE'
            " controllers. If an empty string is provided, any existing"
            " subtype will be removed.")

        parser.add_argument('PACKAGE',
                            help="OVF descriptor or OVA file to edit")
        parser.set_defaults(instance=self)


def expand_list_wildcard(name_list, length, quiet=False):
    """Expand a list containing a wildcard to the desired length.

    Args:
      name_list (list): List of names to assign, or None
      length (list): Length to expand to
      quiet (bool): Silence usual log messages generated by this function.

    Returns:
      list: Expanded list, or empty list if ``name_list`` is None or empty.

    Since various items (NIC names, network names, etc.) are often
    named or numbered sequentially, we provide this API to allow the
    user to specify a wildcard value to permit automatically
    expanding a list of input strings to the desired length.
    The syntax for the wildcard option is ``{`` followed by a number
    (indicating the starting index for the name) followed by ``}``.

    Examples:
      ::

        >>> expand_list_wildcard(None, 3)
        []
        >>> expand_list_wildcard(["eth{0}"], 3)
        ['eth0', 'eth1', 'eth2']
        >>> expand_list_wildcard(["mgmt0", "eth{10}"], 4)
        ['mgmt0', 'eth10', 'eth11', 'eth12']
    """
    if not name_list:
        return []
    if len(name_list) < length:
        if not quiet:
            logger.info("Expanding list %s to %d entries", name_list, length)
        # Extract the pattern and remove it from the list
        pattern = name_list[-1]
        name_list = name_list[:-1]
        # Look for the magic string in the pattern
        match = re.search(r"{(\d+)}", pattern)
        if match:
            value = int(match.group(1))
        else:
            value = 0
        while len(name_list) < length:
            name_list.append(re.sub(r"{\d+}", str(value), pattern))
            value += 1
        if not quiet:
            logger.info("New list is %s", name_list)

    return name_list


def guess_list_wildcard(known_values):
    """Inverse of :func:`expand_list_wildcard`. Guess the wildcard for a list.

    Args:
      known_values (list): Values to guess from

    Returns:
      list: Guessed wildcard list, or None if unable to guess

    Examples:
      ::

        >>> guess_list_wildcard(['foo', 'bar', 'baz'])
        >>> guess_list_wildcard(['foo1', 'foo2', 'foo3'])
        ['foo{1}']
        >>> guess_list_wildcard(['foo', 'bar', 'baz3', 'baz4', 'baz5'])
        ['foo', 'bar', 'baz{3}']
        >>> guess_list_wildcard(['Eth0/1', 'Eth0/2', 'Eth0/3'])
        ['Eth0/{1}']
        >>> guess_list_wildcard(['Eth0/0', 'Eth1/0', 'Eth2/0'])
        ['Eth{0}/0']
        >>> guess_list_wildcard(['fake1', 'fake2', 'real4', 'real5'])
        ['fake1', 'fake2', 'real{4}']
    """
    logger.debug("Attempting to infer a pattern from %s", known_values)
    # Guess sequences ending with simple N, N+1, N+2
    for value_index in range(0, len(known_values)-1):
        current_value = known_values[value_index]
        split_val = alphanum_split(current_value)
        for token_index in range(0, len(split_val)):
            token = split_val[token_index]
            if not isinstance(token, int):
                continue
            prefix = "".join([str(k) for k in split_val[:token_index]])
            suffix = "".join([str(k) for k in split_val[token_index+1:]])
            logger.debug("Possible next value for %s is %s%i%s",
                         current_value, prefix, token+1, suffix)
            possible_next = prefix + str(token + 1) + suffix
            if known_values[value_index+1] == possible_next:
                match_pattern = prefix + "{" + str(token) + "}" + suffix
                logger.debug("Match pattern is %s", match_pattern)
                possible_name_list = (known_values[:value_index] +
                                      [match_pattern])
                logger.debug("Checking possible name list %s",
                             possible_name_list)
                if expand_list_wildcard(possible_name_list,
                                        len(known_values),
                                        quiet=True) == known_values:
                    return possible_name_list
                logger.debug("No joy")

    logger.debug("Unable to guess a pattern")
    return None


command_classes.append(COTEditHardware)


if __name__ == "__main__":   # pragma: no cover
    import doctest
    doctest.testmod()
