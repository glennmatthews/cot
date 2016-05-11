#!/usr/bin/env python
#
# edit_hardware.py - Implements "edit-hardware" sub-command
#
# September 2013, Glenn F. Matthews
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

"""Module for editing hardware details of a VM.

**Classes**

.. autosummary::
  :nosignatures:

  COTEditHardware
"""

import argparse
import logging
import re
import textwrap

from .data_validation import natural_sort, no_whitespace, mac_address
from .data_validation import non_negative_int, positive_int, InvalidInputError
from .submodule import COTSubmodule

logger = logging.getLogger(__name__)


class COTEditHardware(COTSubmodule):
    """Edit hardware information (CPUs, RAM, NICs, etc.).

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`,
    :attr:`~COTSubmodule.package`,
    :attr:`~COTSubmodule.output`

    Attributes:
    :attr:`profiles`,
    :attr:`delete_all_other_profiles`,
    :attr:`cpus`,
    :attr:`memory`,
    :attr:`nics`,
    :attr:`nic_type`,
    :attr:`mac_addresses_list`,
    :attr:`nic_networks`,
    :attr:`nic_names`,
    :attr:`serial_ports`,
    :attr:`serial_connectivity`,
    :attr:`scsi_subtype`,
    :attr:`ide_subtype`,
    :attr:`virtual_system_type`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTEditHardware, self).__init__(UI)
        self.profiles = None
        """Configuration profile(s) to edit."""
        self.delete_all_other_profiles = False
        """Delete all profiles other than those set in :attr:`profiles`."""
        self._cpus = None
        self._memory = None
        self._nics = None
        self._nic_type = None
        self.mac_addresses_list = None
        """List of MAC addresses to set."""
        self.nic_networks = None
        """List of NIC-to-network mappings.

        Can use wildcards as described in :meth:`expand_list_wildcard`.
        """
        self.nic_names = None
        """List of NIC name strings.

        Can use wildcards as described in :meth:`expand_list_wildcard`.
        """
        self._serial_ports = None
        self.serial_connectivity = None
        """List of serial connection strings."""
        self.scsi_subtype = None
        """Subtype string for SCSI controllers"""
        self.ide_subtype = None
        """Subtype string for IDE controllers"""
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
        self.vm.platform.validate_cpu_count(value)
        self._cpus = value

    @property
    def memory(self):
        """Amount of RAM (in megabytes) to set."""
        return self._memory

    @memory.setter
    def memory(self, value):
        value = str(value)
        # We like to see memory input in the form "4096M" or "4 GB"
        MEMORY_REGEXP = r"^\s*(\d+)\s*([mMgG])?[bB]?\s*$"
        match = re.match(MEMORY_REGEXP, value)
        if not match:
            raise InvalidInputError("Could not parse memory string '{0}'"
                                    .format(value))
        mem_value = int(match.group(1))
        if mem_value <= 0:
            raise InvalidInputError("Memory must be greater than zero")
        if match.group(2) == 'M' or match.group(2) == 'm':
            # default
            logger.debug("Memory specified in megabytes")
            pass
        elif match.group(2) == 'G' or match.group(2) == 'g':
            logger.debug("Memory specified in gigabytes - "
                         "converting to megabytes")
            mem_value *= 1024
        else:
            # Try to be clever and guess the units
            if mem_value <= 64:
                logger.warning("Memory units not specified, "
                               "guessing '{0}' means '{0}GB'"
                               .format(mem_value))
                mem_value *= 1024
            else:
                logger.warning("Memory units not specified, "
                               "guessing '{0}' means '{0}MB'"
                               .format(mem_value))
                pass
        self.vm.platform.validate_memory_amount(mem_value)
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
        self.vm.platform.validate_nic_count(value)
        self._nics = value

    @property
    def nic_type(self):
        """NIC type string to set."""
        return self._nic_type

    @nic_type.setter
    def nic_type(self, value):
        self.vm.platform.validate_nic_type(value)
        self._nic_type = value

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
        self.vm.platform.validate_serial_count(value)
        self._serial_ports = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        # Need some work to do!
        if (
                self.profiles is None and
                self.delete_all_other_profiles is False and
                self.cpus is None and
                self.memory is None and
                self.nics is None and
                self.nic_type is None and
                self.mac_addresses_list is None and
                self.nic_networks is None and
                self.nic_names is None and
                self.serial_ports is None and
                self.serial_connectivity is None and
                self.scsi_subtype is None and
                self.ide_subtype is None and
                self.virtual_system_type is None
        ):
            return (False, "No work requested! Please specify at least "
                    "one hardware change")
        return super(COTEditHardware, self).ready_to_run()

    def run(self):
        """Do the actual work of this submodule.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTEditHardware, self).run()

        if self.profiles is not None and self.virtual_system_type is not None:
            self.UI.confirm_or_die(
                "VirtualSystemType is not filtered by configuration profile. "
                "Requested system type(s) '{0}' will be set for ALL profiles, "
                "not just profile(s) {1}. Continue?"
                .format(" ".join(self.virtual_system_type), self.profiles))

        vm = self.vm

        if self.profiles is not None:
            profile_list = vm.config_profiles
            for profile in self.profiles:
                if profile not in profile_list:
                    self.UI.confirm_or_die(
                        "Profile '{0}' does not exist. Create it?"
                        .format(profile))
                    label = self.UI.get_input(
                        "Please enter a label for this configuration profile",
                        profile)
                    desc = self.UI.get_input(
                        "Please enter a description for this "
                        "configuration profile", label)
                    vm.create_configuration_profile(profile, label=label,
                                                    description=desc)

        if self.delete_all_other_profiles:
            if self.profiles is None:
                self.UI.confirm_or_die(
                    "--delete-all-other-profiles was specified but no "
                    "--profiles was specified. Really proceed to delete ALL "
                    "configuration profiles?")
                profiles_to_delete = vm.config_profiles
            else:
                profiles_to_delete = list(set(vm.config_profiles) -
                                          set(self.profiles))
            for profile in profiles_to_delete:
                if self.profiles is not None:
                    if not self.UI.confirm("Delete profile {0}?"
                                           .format(profile)):
                        logger.verbose("Skipping deletion of profile {0}"
                                       .format(profile))
                        continue
                # else (profiles == None) we already confirmed earlier
                vm.delete_configuration_profile(profile)

        if self.virtual_system_type is not None:
            vm.system_types = self.virtual_system_type

        if self.cpus is not None:
            vm.set_cpu_count(self.cpus, self.profiles)

        if self.memory is not None:
            vm.set_memory(self.memory, self.profiles)

        if self.nic_type is not None:
            vm.set_nic_type(self.nic_type, self.profiles)

        nics_dict = vm.get_nic_count(self.profiles)
        if self.nics is not None:
            for (profile, count) in nics_dict.items():
                if self.nics < count:
                    self.UI.confirm_or_die(
                        "Profile {0} currently has {1} NIC(s). "
                        "Delete {2} NIC(s) to reduce to {3} total?"
                        .format(profile, count,
                                (count - self.nics), self.nics))
            vm.set_nic_count(self.nics, self.profiles)

        nics_dict = vm.get_nic_count(self.profiles)
        max_nics = max(nics_dict.values())

        if self.nic_networks is not None:
            existing_networks = vm.networks
            new_networks = self.expand_list_wildcard(self.nic_networks,
                                                     max_nics)
            # Convert nic_networks to a set to merge duplicate entries
            for network in natural_sort(set(new_networks)):
                if network not in existing_networks:
                    self.UI.confirm_or_die(
                        "Network {0} is not currently defined. "
                        "Create it?".format(network))
                    desc = self.UI.get_input(
                        "Please enter a description for this network", network)
                    vm.create_network(network, desc)
            vm.set_nic_networks(new_networks, self.profiles)

        if self.mac_addresses_list is not None:
            vm.set_nic_mac_addresses(self.mac_addresses_list, self.profiles)

        if self.nic_names is not None:
            names = self.expand_list_wildcard(self.nic_names, max_nics)
            vm.set_nic_names(names, self.profiles)

        if self.serial_ports is not None:
            serial_dict = vm.get_serial_count(self.profiles)
            for (profile, count) in serial_dict.items():
                if self.serial_ports < count:
                    self.UI.confirm_or_die(
                        "Profile {0} currently has {1} serial port(s). "
                        "Delete {2} port(s) to reduce to {3} total?"
                        .format(profile, count, (count - self.serial_ports),
                                self.serial_ports))
            vm.set_serial_count(self.serial_ports, self.profiles)

        if self.serial_connectivity is not None:
            serial_dict = vm.get_serial_count(self.profiles)
            for (profile, count) in serial_dict.items():
                if len(self.serial_connectivity) < count:
                    self.UI.confirm_or_die(
                        "There are {0} serial port(s) under profile {1}, but "
                        "you have specified connectivity information for only "
                        "{2}. "
                        "\nThe remaining ports will be unreachable. Continue?"
                        .format(count, profile,
                                len(self.serial_connectivity)))
            vm.set_serial_connectivity(self.serial_connectivity, self.profiles)

        if self.scsi_subtype is not None:
            vm.set_scsi_subtype(self.scsi_subtype, self.profiles)

        if self.ide_subtype is not None:
            vm.set_ide_subtype(self.ide_subtype, self.profiles)

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        :param object parent: Subparser grouping object returned by
            :meth:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
        wrapper = textwrap.TextWrapper(width=self.UI.terminal_width - 1,
                                       initial_indent='  ',
                                       subsequent_indent='  ')
        p = parent.add_parser(
            'edit-hardware', add_help=False,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=self.UI.fill_usage("edit-hardware", [
                "PACKAGE [-o OUTPUT] -v TYPE [TYPE2 ...]",
                "PACKAGE [-o OUTPUT] \
[-p PROFILE [PROFILE2 ...] [--delete-all-other-profiles]] [-c CPUS] \
[-m MEMORY] [-n NICS] [--nic-type {e1000,virtio,vmxnet3}] \
[-N NETWORK [NETWORK2 ...]] [-M MAC1 [MAC2 ...]] \
[--nic-names NAME1 [NAME2 ...]] [-s SERIAL_PORTS] [-S URI1 [URI2 ...]] \
[--scsi-subtype SCSI_SUBTYPE] [--ide-subtype IDE_SUBTYPE]",
            ]),
            help="Edit virtual machine hardware properties of an OVF",
            description="Edit hardware properties of the specified OVF or OVA",
            epilog=("Notes:\n" + wrapper.fill(
                "The --nic-names and --nic-networks options support the use"
                " of a wildcard value to automatically generate a series of"
                " consecutively numbered names. The syntax for the wildcard"
                " option is '{' followed by a number to start incrementing"
                " from, followed by '}'. See examples below."
            ) + "\n\n" + self.UI.fill_examples([
                ('Create a new profile named "1CPU-8GB" with 1 CPU and 8'
                 ' gigabytes of RAM',
                 'cot edit-hardware csr1000v.ova --output csr1000v_custom.ova'
                 ' --profile 1CPU-4GB --cpus 1 --memory 8GB'),
                ("Wildcard example - without caring about how many NICs are"
                 " defined in the input OVA, rename all of the NICs in the"
                 " output OVA as 'Ethernet0/10', 'Ethernet0/11',"
                 " 'Ethernet0/12', etc., and map them to networks"
                 " 'Ethernet0_10', 'Ethernet0_11', 'Ethernet0_12', etc.",
                 'cot edit-hardware input.ova -o output.ova'
                 ' --nic-names "Ethernet0/{10}"'
                 ' --nic-networks "Ethernet0_{10}"'),
                ("Combination of fixed and wildcarded names - rename the NICs"
                 " in the output OVA as 'mgmt', 'eth0', 'eth1', 'eth2'...",
                 'cot edit-hardware input.ova -o output.ova'
                 ' --nic-names "mgmt" "eth{0}"'),
            ])))

        g = p.add_argument_group("general options")

        g.add_argument('-h', '--help', action='help',
                       help="Show this help message and exit")
        g.add_argument('-o', '--output',
                       help="Name/path of new OVF/OVA package to create "
                       "instead of updating the existing OVF")
        g.add_argument('-v', '--virtual-system-type', nargs='+',
                       type=no_whitespace, metavar=('TYPE', 'TYPE2'),
                       help="Change virtual system type(s) supported by "
                       "this OVF/OVA package.")
        g.add_argument('-p', '--profiles', nargs='+', type=no_whitespace,
                       metavar=('PROFILE', 'PROFILE2'),
                       help="Make hardware changes only under the given "
                       "configuration profile(s). (default: changes apply "
                       "to all profiles)")
        g.add_argument('--delete-all-other-profiles', action='store_true',
                       help="Delete all configuration profiles other than"
                       " those specified with the --profiles option")

        g = p.add_argument_group("computational hardware options")

        g.add_argument('-c', '--cpus', type=positive_int,
                       help="Set the number of CPUs.")
        g.add_argument('-m', '--memory',
                       help="Set the amount of RAM. "
                       '(Examples: "4096MB", "4GB")')

        g = p.add_argument_group("network interface options")

        g.add_argument('-n', '--nics', type=non_negative_int,
                       help="Set the number of NICs.")
        g.add_argument('--nic-type',
                       choices=['e1000', 'virtio', 'vmxnet3'],
                       help="Set the hardware type for all NICs. "
                       "(default: do not change existing NICs, and new "
                       "NICs added will match the existing type.)")
        g.add_argument('--nic-names', action='append', nargs='+',
                       metavar=('NAME1', 'NAME2'),
                       help="Specify a list of one or more NIC names or "
                       "patterns to apply to NIC devices. See Notes.")
        g.add_argument('-N', '--nic-networks', nargs='+',
                       metavar=('NETWORK', 'NETWORK2'),
                       help="Specify a series of one or more network names "
                       "or patterns to map NICs to. See Notes.")
        g.add_argument('-M', '--mac-addresses-list', type=mac_address,
                       metavar=('MAC1', 'MAC2'), action='append', nargs='+',
                       help="Specify a list of MAC addresses for the NICs. "
                       "If N MACs are specified, the first (N-1) NICs "
                       "will receive the first (N-1) MACs, and all "
                       "remaining NICs will receive the Nth MAC")

        g = p.add_argument_group("serial port options")

        g.add_argument('-s', '--serial-ports', type=non_negative_int,
                       help="Set the number of serial ports.")
        g.add_argument('-S', '--serial-connectivity',
                       metavar=('URI1', 'URI2'), action='append', nargs='+',
                       help="Specify a series of connectivity strings "
                       '(URIs such as "telnet://localhost:9101") to map '
                       "serial ports to. If fewer URIs than serial ports "
                       "are specified, the remaining ports will be "
                       "unmapped.""")

        g = p.add_argument_group("disk and disk controller options")

        g.add_argument('--scsi-subtype',
                       help='Set resource subtype (such as "lsilogic" or '
                       '"virtio") for all SCSI controllers. If an empty '
                       "string is provided, any existing subtype will be "
                       "removed.")
        g.add_argument('--ide-subtype',
                       help='Set resource subtype (such as "virtio") for '
                       "all IDE controllers. If an empty string is "
                       "provided, any existing subtype will be removed.")

        p.add_argument('PACKAGE',
                       help="OVF descriptor or OVA file to edit")
        p.set_defaults(instance=self)

        storage['edit-hardware'] = p

    def expand_list_wildcard(self, name_list, length):
        """Expand a list containing a wildcard to the desired length.

        Since various items (NIC names, network names, etc.) are often
        named or numbered sequentially, we provide this API to allow the
        user to specify a wildcard value to permit automatically
        expanding a list of input strings to the desired length.
        The syntax for the wildcard option is ``{`` followed by a number
        (indicating the starting index for the name) followed by ``}``.
        Examples:

        ``["eth{0}"]``
          ``Expands to ["eth0", "eth1", "eth2", ...]``
        ``["mgmt0" "eth{10}"]``
          ``Expands to ["mgmt0", "eth10", "eth11", "eth12", ...]``

        :param list name_list: List of names to assign.
        :param list length: Length to expand to
        :return: Expanded list
        """
        if len(name_list) < length:
            logger.info("Expanding list {0} to {1} entries"
                        .format(name_list, length))
            # Extract the pattern and remove it from the list
            pattern = name_list[-1]
            name_list = name_list[:-1]
            # Look for the magic string in the pattern
            match = re.search("{(\d+)}", pattern)
            if match:
                i = int(match.group(1))
            else:
                i = 0
            while len(name_list) < length:
                name_list.append(re.sub("{\d+}", str(i), pattern))
                i += 1
            logger.info("New list is {0}".format(name_list))

        return name_list
