#!/usr/bin/env python
#
# edit_hardware.py - Implements "edit-hardware" sub-command
#
# September 2013, Glenn F. Matthews
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

import argparse
import logging
import os.path
import re
import sys

from .data_validation import *
from .data_validation import ValueUnsupportedError, InvalidInputError
from .vm_context_manager import VMContextManager

logger = logging.getLogger(__name__)

def edit_hardware(UI,
                  PACKAGE,
                  output=None,
                  profiles=None,
                  cpus=None,
                  memory=None,
                  nics=None,
                  nic_type=None,
                  mac_addresses_list=None,
                  nic_networks=None,
                  nic_names=None,
                  serial_ports=None,
                  serial_connectivity=None,
                  scsi_subtype=None,
                  ide_subtype=None,
                  virtual_system_type=None,
                  **kwargs):
    """Edit hardware information (CPUs, RAM, NICs, etc.)"""

    if (cpus is None and
        memory is None and
        nics is None and
        nic_type is None and
        mac_addresses_list is None and
        nic_networks is None and
        nic_names is None and
        profiles is None and
        serial_ports is None and
        serial_connectivity is None and
        scsi_subtype is None and
        ide_subtype is None and
        virtual_system_type is None):
        raise InvalidInputError(
            "No work requested! Please specify at least one hardware change")

    # Additional input validation
    if cpus is not None and cpus < 1:
        raise InvalidInputError("'--cpus {0}' is not valid; must be at least 1"
                                .format(cpus))

    if profiles is not None and virtual_system_type is not None:
        UI.confirm_or_die("VirtualSystemType is not filtered by configuration "
                          "profile. Requested system type(s) '{0}' will be set "
                          "for ALL profiles, not just profile(s) {1}. Continue?"
                          .format(" ".join(virtual_system_type), profiles))

    with VMContextManager(PACKAGE, output) as vm:
        platform = vm.get_platform()

        if profiles is not None:
            profile_list = vm.get_configuration_profile_ids()
            for profile in profiles:
                if not profile in profile_list:
                    UI.confirm_or_die("Profile '{0}' does not exist. Create it?"
                                      .format(profile))
                    label = UI.get_input("Please enter a label for this "
                                         "configuration profile", profile)
                    desc = UI.get_input("Please enter a description for this "
                                        "configuration profile", label)
                    vm.create_configuration_profile(profile, label=label,
                                                    description=desc)

        if virtual_system_type is not None:
            vm.set_system_type(virtual_system_type)

        if cpus is not None:
            vm.set_cpu_count(cpus, profiles)

        if memory is not None:
            # Parse the input to figure out what was really meant
            match = re.match(r"^(\d+)([mMgG])?[bB]?$", memory)
            if not match:
                raise InvalidInputError("Unable to parse '--memory {0}'"
                                .format(memory))
            mem_value = int(match.group(1))
            if mem_value == 0:
                raise InvalidInputError("Memory must be a non-zero amount")
            if match.group(2) == 'M' or match.group(2) == 'm':
                # default
                logger.debug("Memory specified in megabytes")
                pass
            elif match.group(2) == 'G' or match.group(2) == 'g':
                logger.debug("Memory specified in gigabytes - "
                             "converting to megabytes")
                mem_value *= 1024
            else:
                # Try to be clever and guess the amount of RAM
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
            vm.set_memory(mem_value, profiles)

        if nic_type is not None:
            vm.set_nic_type(nic_type, profiles)

        if nics is not None:
            platform.validate_nic_count(nics)
            nics_dict = vm.get_nic_count(profiles)
            for (profile, count) in nics_dict.items():
                if nics < count:
                    UI.confirm_or_die("Profile {0} currently has {1} NIC(s). "
                                      "Delete {2} NIC(s) to reduce to "
                                      "{3} total?"
                                      .format(profile, count,
                                              (count - nics),
                                              nics))
            vm.set_nic_count(nics, profiles)

        if nic_networks is not None:
            existing_networks = vm.get_network_list()
            # Convert nic_networks to a set to merge duplicate entries
            for network in natural_sort(set(nic_networks)):
                if not network in existing_networks:
                    UI.confirm_or_die("Network {0} is not currently defined. "
                                      "Create it?".format(network))
                    desc = UI.get_input("Please enter a description for "
                                        "this network", network)
                    vm.create_network(network, desc)
            vm.set_nic_networks(nic_networks, profiles)

        if mac_addresses_list is not None:
            vm.set_nic_mac_addresses(mac_addresses_list, profiles)

        if nic_names is not None:
            vm.set_nic_names(nic_names, profiles)

        if serial_ports is not None:
            platform.validate_serial_count(serial_ports)
            serial_dict = vm.get_serial_count(profiles)
            for (profile, count) in serial_dict.items():
                if serial_ports < count:
                    UI.confirm_or_die(
                        "Profile {0} currently has {1} serial port(s). "
                        "Delete {2} port(s) to reduce to {3} total?"
                        .format(profile, count, (count - serial_ports),
                                serial_ports))
            vm.set_serial_count(serial_ports, profiles)

        if serial_connectivity is not None:
            serial_dict = vm.get_serial_count(profiles)
            for (profile, count) in serial_dict.items():
                if len(serial_connectivity) < count:
                    UI.confirm_or_die(
                        "{0} has {1} serial port(s) under profile {2}, but you "
                        "have specified connectivity information for only {3}. "
                        "\nThe remaining ports will be unreachable. Continue?"
                        .format(output, count, profile,
                                len(serial_connectivity)))
            vm.set_serial_connectivity(serial_connectivity, profiles)

        if scsi_subtype is not None:
            vm.set_scsi_subtype(scsi_subtype, profiles)

        if ide_subtype is not None:
            vm.set_ide_subtype(ide_subtype, profiles)

def create_subparser(parent):
    p = parent.add_parser(
        'edit-hardware', add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=("""
  {0} edit-hardware --help
  {0} [-f] [-v] edit-hardware PACKAGE [-o OUTPUT] -v TYPE [TYPE2 ...]
  {0} [-f] [-v] edit-hardware PACKAGE [-o OUTPUT] [-p PROFILE [PROFILE2 ...]]
                              [-c CPUS] [-m MEMORY]
                              [-n NICS] [--nic-type {{e1000,virtio,vmxnet3}}]
                              [-N NETWORK [NETWORK2 ...]] [-M MAC1 [MAC2 ...]]
                              [--nic-names NAME1 [NAME2 ...]]
                              [-s SERIAL_PORTS] [-S URI1 [URI2 ...]]
                              [--scsi-subtype SCSI_SUBTYPE]
                              [--ide-subtype IDE_SUBTYPE]"""
               .format(os.path.basename(sys.argv[0]))),
        help="""Edit virtual machine hardware properties of an OVF""",
        description="""Edit hardware properties of the specified OVF or OVA""",
        epilog="""
Examples:

  {0} edit-hardware csr1000v.ova --output csr1000v_custom.ova \\
        --profile 1CPU-4GB --cpus 1 --memory 4GB
    Create a new profile named "1CPU-4GB" with 1 CPU and 4 GB of RAM

  {0} edit-hardware input.ova -o output.ova --nic-names 'management' 'eth{{0}}'
    Rename the NICs in the output OVA as 'management', 'eth0', 'eth1', 'eth2'...

  {0} edit-hardware input.ova -o output.ova --nic-names 'Ethernet0/{{10}}'
    Rename the NICs in the output OVA as 'Ethernet0/10', 'Ethernet0/11',
    'Ethernet0/12', etc.

    """.format(os.path.basename(sys.argv[0])))

    group = p.add_argument_group("general options")

    group.add_argument('-h', '--help', action='help',
                       help="""Show this help message and exit""")
    group.add_argument('-o', '--output',
                       help="""Name/path of new OVF/OVA package to create """
                       """instead of updating the existing OVF""")
    group.add_argument('-v', '--virtual-system-type', nargs='+',
                       type=no_whitespace, metavar=('TYPE', 'TYPE2'),
                       help="""Change virtual system type(s) supported by """
                       """this OVF/OVA package.""")
    group.add_argument('-p', '--profiles', nargs='+', type=no_whitespace,
                       metavar=('PROFILE', 'PROFILE2'),
                       help="""Make hardware changes only under the given """
                       """configuration profile(s). (default: changes apply """
                       """to all profiles)""")

    group = p.add_argument_group("computational hardware options")

    group.add_argument('-c', '--cpus', type=positive_int,
                       help="""Set the number of CPUs.""")
    group.add_argument('-m', '--memory',
                       help="""Set the amount of RAM. """
                       """(Examples: "4096MB", "4GB")""")

    group = p.add_argument_group("network interface options")

    group.add_argument('-n', '--nics', type=non_negative_int,
                       help="""Set the number of NICs.""")
    group.add_argument('--nic-type',
                       choices=['e1000', 'virtio', 'vmxnet3'],
                       help="""Set the hardware type for all NICs. """
                       """(default: do not change existing NICs, and new """
                       """NICs added will match the existing type.)""")
    group.add_argument('-N', '--nic-networks', nargs='+',
                       metavar=('NETWORK', 'NETWORK2'),
                       help="""Specify a series of one or more network names """
                       """to map NICs to. If N network names are specified, """
                       """the first (N-1) NICs will be mapped to the first """
                       """(N-1) networks and all remaining NICs will be """
                       """mapped to the Nth network.""")
    group.add_argument('-M', '--mac-addresses-list', type=mac_address,
                       metavar=('MAC1', 'MAC2'), nargs='+',
                       help="""Specify a list of MAC addresses for the NICs. """
                       """If N MACs are specified, the first (N-1) NICs """
                       """will receive the first (N-1) MACs, and all """
                       """remaining NICs will receive the Nth MAC""")
    group.add_argument('--nic-names', nargs='+',
                       metavar=('NAME1', 'NAME2'),
                       help="""Specify a list of one or more NIC names or """
                       """patterns to apply to NIC devices. """
                       """If N names/patterns are specified, the first (N-1) """
                       """NICs will receive the first (N-1) names and """
                       """remaining NICs will be named based on the """
                       """name or pattern of the Nth item. See examples.""")

    group = p.add_argument_group("serial port options")

    group.add_argument('-s', '--serial-ports', type=non_negative_int,
                       help="""Set the number of serial ports.""")
    group.add_argument('-S', '--serial-connectivity',
                       metavar=('URI1', 'URI2'), nargs='+',
                       help="""Specify a series of connectivity strings """
                       """(URIs such as "telnet://localhost:9101") to map """
                       """serial ports to. If fewer URIs than serial ports """
                       """are specified, the remaining ports will be """
                       """unmapped.""")

    group = p.add_argument_group("disk and disk controller options")

    group.add_argument('--scsi-subtype',
                       help="""Set resource subtype (such as "lsilogic" or """
                       """"virtio") for all SCSI controllers. If an empty """
                       """string is provided, any existing subtype will be """
                       """removed.""")
    group.add_argument('--ide-subtype',
                       help="""Set resource subtype (such as "virtio") for """
                       """all IDE controllers. If an empty string is """
                       """provided, any existing subtype will be removed.""")

    p.add_argument('PACKAGE',
                   help="""OVF descriptor or OVA file to edit""")
    p.set_defaults(func=edit_hardware)

    return 'edit-hardware', p
