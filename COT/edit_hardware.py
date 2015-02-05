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

import argparse
import logging
import re

from .data_validation import natural_sort, no_whitespace, mac_address
from .data_validation import non_negative_int, positive_int
from .submodule import COTSubmodule

logger = logging.getLogger(__name__)


class COTEditHardware(COTSubmodule):
    """Edit hardware information (CPUs, RAM, NICs, etc.)"""

    def __init__(self, UI):
        super(COTEditHardware, self).__init__(
            UI,
            [
                "PACKAGE",
                "output",
                "profiles",
                "cpus",
                "memory",
                "nics",
                "nic_type",
                "mac_addresses_list",
                "nic_networks",
                "nic_names",
                "serial_ports",
                "serial_connectivity",
                "scsi_subtype",
                "ide_subtype",
                "virtual_system_type",
            ])

    # We like to see memory input in the form "4096M" or "4 GB"
    MEMORY_REGEXP = r"^\s*(\d+)\s*([mMgG])?[bB]?\s*$"

    def validate_arg(self, arg, value):
        """Check whether it's OK to set the given argument to the given value.
        Returns either (True, massaged_value) or (False, reason)"""
        valid, value_or_reason = super(COTEditHardware, self).validate_arg(
            arg, value)
        if not valid or value_or_reason is None:
            return valid, value_or_reason
        value = value_or_reason

        try:
            if arg == "cpus":
                value = int(value)
                if value < 1:
                    return False, "CPU count must be at least 1"
                self.vm.get_platform().validate_cpu_count(value)
            elif arg == "memory":
                value = str(value)
                match = re.match(self.MEMORY_REGEXP, value)
                if not match:
                    return (False, "Could not parse memory string '{0}'"
                            .format(value))
                mem_value = int(match.group(1))
                if mem_value <= 0:
                    return False, "Memory must be greater than zero"
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
                self.vm.get_platform().validate_memory_amount(mem_value)
                return True, mem_value
            elif arg == "nics":
                value = int(value)
                self.vm.get_platform().validate_nic_count(value)
            elif arg == "nic_type":
                self.vm.get_platform().validate_nic_type(value)
            elif arg == "serial_ports":
                value = int(value)
                self.vm.get_platform().validate_serial_count(value)
        except ValueError as e:
            return False, str(e)

        return valid, value

    def ready_to_run(self):
        """Are we ready to go?
        Returns the tuple (ready, reason)"""

        # Need some work to do!
        work_to_do = False
        for (key, value) in self.args.items():
            if key == "PACKAGE" or key == "output":
                continue
            elif value is not None:
                work_to_do = True
                break
        if not work_to_do:
            return (False, "No work requested! Please specify at least "
                    "one hardware change")
        return super(COTEditHardware, self).ready_to_run()

    def run(self):
        super(COTEditHardware, self).run()

        profiles = self.get_value("profiles")
        virtual_system_type = self.get_value("virtual_system_type")
        if profiles is not None and virtual_system_type is not None:
            self.UI.confirm_or_die(
                "VirtualSystemType is not filtered by configuration profile. "
                "Requested system type(s) '{0}' will be set for ALL profiles, "
                "not just profile(s) {1}. Continue?"
                .format(" ".join(virtual_system_type), profiles))

        vm = self.vm

        if profiles is not None:
            profile_list = vm.get_configuration_profile_ids()
            for profile in profiles:
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

        if virtual_system_type is not None:
            vm.set_system_type(virtual_system_type)

        cpus = self.get_value("cpus")
        if cpus is not None:
            vm.set_cpu_count(cpus, profiles)

        memory = self.get_value("memory")
        if memory is not None:
            vm.set_memory(memory, profiles)

        nic_type = self.get_value("nic_type")
        if nic_type is not None:
            vm.set_nic_type(nic_type, profiles)

        nics = self.get_value("nics")
        if nics is not None:
            nics_dict = vm.get_nic_count(profiles)
            for (profile, count) in nics_dict.items():
                if nics < count:
                    self.UI.confirm_or_die(
                        "Profile {0} currently has {1} NIC(s). "
                        "Delete {2} NIC(s) to reduce to {3} total?"
                        .format(profile, count, (count - nics), nics))
            vm.set_nic_count(nics, profiles)

        nic_networks = self.get_value("nic_networks")
        if nic_networks is not None:
            existing_networks = vm.get_network_list()
            # Convert nic_networks to a set to merge duplicate entries
            for network in natural_sort(set(nic_networks)):
                if network not in existing_networks:
                    self.UI.confirm_or_die(
                        "Network {0} is not currently defined. "
                        "Create it?".format(network))
                    desc = self.UI.get_input(
                        "Please enter a description for this network", network)
                    vm.create_network(network, desc)
            vm.set_nic_networks(nic_networks, profiles)

        mac_addresses_list = self.get_value("mac_addresses_list")
        if mac_addresses_list is not None:
            vm.set_nic_mac_addresses(mac_addresses_list, profiles)

        nic_names = self.get_value("nic_names")
        if nic_names is not None:
            vm.set_nic_names(nic_names, profiles)

        serial_ports = self.get_value("serial_ports")
        if serial_ports is not None:
            serial_dict = vm.get_serial_count(profiles)
            for (profile, count) in serial_dict.items():
                if serial_ports < count:
                    self.UI.confirm_or_die(
                        "Profile {0} currently has {1} serial port(s). "
                        "Delete {2} port(s) to reduce to {3} total?"
                        .format(profile, count, (count - serial_ports),
                                serial_ports))
            vm.set_serial_count(serial_ports, profiles)

        serial_connectivity = self.get_value("serial_connectivity")
        if serial_connectivity is not None:
            serial_dict = vm.get_serial_count(profiles)
            for (profile, count) in serial_dict.items():
                if len(serial_connectivity) < count:
                    self.UI.confirm_or_die(
                        "There are {0} serial port(s) under profile {1}, but "
                        "you have specified connectivity information for only "
                        "{2}. "
                        "\nThe remaining ports will be unreachable. Continue?"
                        .format(count, profile,
                                len(serial_connectivity)))
            vm.set_serial_connectivity(serial_connectivity, profiles)

        scsi_subtype = self.get_value("scsi_subtype")
        if scsi_subtype is not None:
            vm.set_scsi_subtype(scsi_subtype, profiles)

        ide_subtype = self.get_value("ide_subtype")
        if ide_subtype is not None:
            vm.set_ide_subtype(ide_subtype, profiles)

    def create_subparser(self, parent):
        p = parent.add_parser(
            'edit-hardware', add_help=False,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage="""
  cot edit-hardware --help
  cot <opts> edit-hardware PACKAGE [-o OUTPUT] -v TYPE [TYPE2 ...]
  cot <opts> edit-hardware PACKAGE [-o OUTPUT] [-p PROFILE [PROFILE2 ...]]
                           [-c CPUS] [-m MEMORY]
                           [-n NICS] [--nic-type {{e1000,virtio,vmxnet3}}]
                           [-N NETWORK [NETWORK2 ...]] [-M MAC1 [MAC2 ...]]
                           [--nic-names NAME1 [NAME2 ...]]
                           [-s SERIAL_PORTS] [-S URI1 [URI2 ...]]
                           [--scsi-subtype SCSI_SUBTYPE]
                           [--ide-subtype IDE_SUBTYPE]""",
            help="Edit virtual machine hardware properties of an OVF",
            description="Edit hardware properties of the specified OVF or OVA",
            epilog="""
Examples:

  cot edit-hardware csr1000v.ova --output csr1000v_custom.ova \\
        --profile 1CPU-4GB --cpus 1 --memory 4GB
    Create a new profile named "1CPU-4GB" with 1 CPU and 4 GB of RAM

  cot edit-hardware input.ova -o output.ova --nic-names 'mgmt' 'eth{{0}}'
    Rename the NICs in the output OVA as 'mgmt', 'eth0', 'eth1', 'eth2'...

  cot edit-hardware input.ova -o output.ova --nic-names 'Ethernet0/{{10}}'
    Rename the NICs in the output OVA as 'Ethernet0/10', 'Ethernet0/11',
    'Ethernet0/12', etc.""")

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
        g.add_argument('-N', '--nic-networks', nargs='+',
                       metavar=('NETWORK', 'NETWORK2'),
                       help="Specify a series of one or more network names "
                       "to map NICs to. If N network names are specified, "
                       "the first (N-1) NICs will be mapped to the first "
                       "(N-1) networks and all remaining NICs will be "
                       "mapped to the Nth network.")
        g.add_argument('-M', '--mac-addresses-list', type=mac_address,
                       metavar=('MAC1', 'MAC2'), nargs='+',
                       help="Specify a list of MAC addresses for the NICs. "
                       "If N MACs are specified, the first (N-1) NICs "
                       "will receive the first (N-1) MACs, and all "
                       "remaining NICs will receive the Nth MAC")
        g.add_argument('--nic-names', nargs='+',
                       metavar=('NAME1', 'NAME2'),
                       help="Specify a list of one or more NIC names or "
                       "patterns to apply to NIC devices. "
                       "If N names/patterns are specified, the first (N-1) "
                       "NICs will receive the first (N-1) names and "
                       "remaining NICs will be named based on the "
                       "name or pattern of the Nth item. See examples.")

        g = p.add_argument_group("serial port options")

        g.add_argument('-s', '--serial-ports', type=non_negative_int,
                       help="Set the number of serial ports.")
        g.add_argument('-S', '--serial-connectivity',
                       metavar=('URI1', 'URI2'), nargs='+',
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

        return 'edit-hardware', p
