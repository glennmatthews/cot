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

import logging
import os.path
import re
import sys

from .cli import (subparsers, subparser_lookup,
                  mac_address, no_whitespace, non_negative_int, positive_int,
                  confirm_or_die, get_input)
from .data_validation import natural_sort, ValueUnsupportedError
from .vm_context_manager import VMContextManager

logger = logging.getLogger(__name__)

def edit_hardware(args):
    """Edit hardware information (CPUs, RAM, NICs, etc.)"""

    if (args.cpus is None and args.memory is None and args.nics is None and
        args.nic_type is None and args.mac_addresses_list is None and
        args.nic_networks is None and args.serial_ports is None and
        args.serial_connectivity is None and args.scsi_subtype is None and
        args.ide_subtype is None and args.virtual_system_type is None):
        p_edit_hw.error("No work requested! Please specify at least one "
                        "hardware change")

    # Generic CLI validation beyond what argparse provides:
    if args.cpus is not None and args.cpus < 1:
        p_edit_hw.error("'--cpus {0}' is not valid; must be at least 1"
                        .format(args.cpus))

    if args.profiles is not None and args.virtual_system_type is not None:
        confirm_or_die("VirtualSystemType is not filtered by configuration "
                       "profile. Requested system type(s) '{0}' will be set "
                       "for ALL profiles, not just profile(s) {1}. Continue?"
                       .format(" ".join(args.virtual_system_type),
                               args.profiles),
                       args.force)

    with VMContextManager(args.PACKAGE, args.output) as vm:
        platform = vm.get_platform()

        if args.profiles is not None:
            profile_list = vm.get_configuration_profile_ids()
            for profile in args.profiles:
                if not profile in profile_list:
                    confirm_or_die("Profile '{0}' does not exist. Create it?"
                                   .format(profile), args.force)
                    label = get_input("Please enter a label for this "
                                      "configuration profile",
                                      profile, args.force)
                    desc = get_input("Please enter a description for this "
                                     "configuration profile",
                                     label, args.force)
                    vm.create_configuration_profile(profile, label=label,
                                                    description=desc)

        if args.virtual_system_type is not None:
            vm.set_system_type(args.virtual_system_type)

        if args.cpus is not None:
            try:
                vm.set_cpu_count(args.cpus, args.profiles)
            except ValueUnsupportedError as e:
                p_edit_hw.error(e)

        if args.memory is not None:
            # Parse the CLI to figure out what was really meant
            match = re.match(r"^(\d+)([mMgG])?[bB]?$", args.memory)
            if not match:
                p_edit_hw.error("Unable to parse '--memory {0}'"
                                .format(args.memory))
            mem_value = int(match.group(1))
            if mem_value == 0:
                p_edit_hw.error("Memory must be a non-zero amount")
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
            try:
                vm.set_memory(mem_value, args.profiles)
            except ValueUnsupportedError as e:
                p_edit_hw.error(e)

        if args.nic_type is not None:
            vm.set_nic_type(args.nic_type, args.profiles)

        if args.nics is not None:
            try:
                platform.validate_nic_count(args.nics)
            except ValueUnsupportedError as e:
                p_edit_hw.error(e)
            nics_dict = vm.get_nic_count(args.profiles)
            for (profile, count) in nics_dict.items():
                if args.nics < count:
                    confirm_or_die("Profile {0} currently has {1} NIC(s). "
                                   "Delete {2} NIC(s) to reduce to {3} total?"
                                   .format(profile, count,
                                           (count - args.nics),
                                           args.nics),
                                   args.force)
            try:
                vm.set_nic_count(args.nics, args.profiles)
            except ValueUnsupportedError as e:
                p_edit_hw.error(e)

        if args.nic_networks is not None:
            existing_networks = vm.get_network_list()
            # Convert args.nic_networks to a set to merge duplicate entries
            for network in natural_sort(set(args.nic_networks)):
                if not network in existing_networks:
                    confirm_or_die("Network {0} is not currently defined. "
                                   "Create it?".format(network), args.force)
                    desc = get_input("Please enter a description for "
                                     "this network", network, args.force)
                    vm.create_network(network, desc)
            vm.set_nic_networks(args.nic_networks, args.profiles)

        if args.mac_addresses_list is not None:
            vm.set_nic_mac_addresses(args.mac_addresses_list, args.profiles)


        if args.serial_ports is not None:
            try:
                platform.validate_serial_count(args.serial_ports)
            except ValueUnsupportedError as e:
                p_edit_hw.error(e)
            serial_dict = vm.get_serial_count(args.profiles)
            for (profile, count) in serial_dict.items():
                if args.serial_ports < count:
                    confirm_or_die("Profile {0} currently has {1} serial "
                                   "port(s). Delete {2} port(s) to reduce "
                                   "to {3} total?"
                                   .format(profile, count,
                                           (count - args.serial_ports),
                                           args.serial_ports),
                                   args.force)
            try:
                vm.set_serial_count(args.serial_ports, args.profiles)
            except ValueUnsupportedError as e:
                p_edit_hw.error(e)

        if args.serial_connectivity is not None:
            serial_dict = vm.get_serial_count(args.profiles)
            for (profile, count) in serial_dict.items():
                if len(args.serial_connectivity) < count:
                    confirm_or_die("{0} has {1} serial port(s) under profile "
                                   "{2}, but you have specified connectivity "
                                   "information for only {3}. "
                                   "\nThe remaining ports will be "
                                   "unreachable. Continue?"
                                   .format(args.output, count, profile,
                                           len(args.serial_connectivity)),
                                   args.force)
            vm.set_serial_connectivity(args.serial_connectivity, args.profiles)

        if args.scsi_subtype is not None:
            vm.set_scsi_subtype(args.scsi_subtype, args.profiles)

        if args.ide_subtype is not None:
            vm.set_ide_subtype(args.ide_subtype, args.profiles)


# Add ourselves to the parser options
p_edit_hw = subparsers.add_parser(
    'edit-hardware', add_help=False,
    usage=("""
  {0} edit-hardware --help
  {0} [-f] [-v] edit-hardware PACKAGE [-o OUTPUT] -v TYPE [TYPE2 ...]
  {0} [-f] [-v] edit-hardware PACKAGE [-o OUTPUT] [-p PROFILE [PROFILE2 ...]]
                              [-c CPUS] [-m MEMORY]
                              [-n NICS] [--nic-type {{e1000,virtio,vmxnet3}}]
                              [-N NETWORK [NETWORK2 ...]] [-M MAC1 [MAC2 ...]]
                              [-s SERIAL_PORTS] [-S URI1 [URI2 ...]]
                              [--scsi-subtype SCSI_SUBTYPE]
                              [--ide-subtype IDE_SUBTYPE]"""
           .format(os.path.basename(sys.argv[0]))),
    help="""Edit virtual machine hardware properties of an OVF""",
    description="""Edit hardware properties of the specified OVF or OVA""")
subparser_lookup['edit-hardware'] = p_edit_hw

p_eh_gen = p_edit_hw.add_argument_group("general options")

p_eh_gen.add_argument('-h', '--help', action='help',
                      help="""Show this help message and exit""")
p_eh_gen.add_argument('-o', '--output',
                      help="""Name/path of new OVF/OVA package to create
                              instead of updating the existing OVF""")
p_eh_gen.add_argument('-v', '--virtual-system-type', nargs='+',
                      type=no_whitespace, metavar=('TYPE', 'TYPE2'),
                      help="""Change virtual system type(s) supported by this
                      OVF/OVA package.""")
p_eh_gen.add_argument('-p', '--profiles', nargs='+', type=no_whitespace,
                      metavar=('PROFILE', 'PROFILE2'),
                      help="""Make hardware changes only under the specified
                              configuration profile(s). (default: changes apply
                              to all profiles)""")

p_eh_comp = p_edit_hw.add_argument_group("computational hardware options")

p_eh_comp.add_argument('-c', '--cpus', type=positive_int,
                       help="""Set the number of CPUs.""")
p_eh_comp.add_argument('-m', '--memory',
                       help="""Set the amount of RAM.
                               (Examples: "4096MB", "4GB")""")

p_eh_nic = p_edit_hw.add_argument_group("network interface options")

p_eh_nic.add_argument('-n', '--nics', type=non_negative_int,
                      help="""Set the number of NICs.""")
p_eh_nic.add_argument('--nic-type',
                      choices=['e1000', 'virtio', 'vmxnet3'],
                      help="""Set the hardware type for all NICs.
                              (default: do not change existing NICs, and new
                              NICs added will match the existing type.)""")
p_eh_nic.add_argument('-N', '--nic-networks', nargs='+',
                      metavar=('NETWORK', 'NETWORK2'),
                      help="""Specify a series of one or more network names to
                              map NICs to. If N network names are specified,
                              the first (N-1) NICs will be mapped to the first
                              (N-1) networks and all remaining NICs will be
                              mapped to the Nth network.""")
p_eh_nic.add_argument('-M', '--mac-addresses-list', type=mac_address,
                      metavar=('MAC1', 'MAC2'), nargs='+',
                      help="""Specify a list of MAC addresses for the NICs.
                              If N MACs are specified, the first (N-1) NICs
                              will receive the first (N-1) MACs, and all
                              remaining NICs will receive the Nth MAC""")

p_eh_ser = p_edit_hw.add_argument_group("serial port options")

p_eh_ser.add_argument('-s', '--serial-ports', type=non_negative_int,
                      help="""Set the number of serial ports.""")
p_eh_ser.add_argument('-S', '--serial-connectivity',
                      metavar=('URI1', 'URI2'), nargs='+',
                      help="""Specify a series of connectivity strings (URIs
                              such as "telnet://localhost:9101") to map serial
                              ports to. If fewer URIs than serial ports are
                              specified, the remaining ports will be
                              unmapped.""")

p_eh_disk = p_edit_hw.add_argument_group("disk and disk controller options")

p_eh_disk.add_argument('--scsi-subtype',
                       help="""Set resource subtype (such as "lsilogic" or
                               "virtio") for all SCSI controllers. If an empty
                               string is provided, any existing subtype will be
                               removed.""")
p_eh_disk.add_argument('--ide-subtype',
                       help="""Set resource subtype (such as
                               "virtio") for all IDE controllers. If an empty
                               string is provided, any existing subtype will be
                               removed.""")

p_edit_hw.add_argument('PACKAGE',
                       help="""OVF descriptor or OVA file to edit""")
p_edit_hw.set_defaults(func=edit_hardware)
