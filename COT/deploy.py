#!/usr/bin/env python
#
# deploy.py - Implements "cot deploy" command
#
# June 2014, Kevin A. Keim
# Copyright (c) 2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

import logging
import os.path
import sys
import getpass

from .cli import subparsers, subparser_lookup, argparse, get_input
from .vm_context_manager import VMContextManager
from .vm_description import VMDescription
from COT.helper_tools import check_output
from COT.ovf import *

logger = logging.getLogger(__name__)

def deploy(args):
    # if deploying to esxi use deploy_esxi function
    if args.HYPERVISOR == "esxi":
        deploy_esxi(args)
    else:
        raise NotImplementedError("""No support for deployment to '{0}' at
                                   this time!"""
                                   .format(args.HYPERVISOR))

def deploy_esxi(args):
    # ensure user entered a server
    if args.server is None:
        p_deploy.error("No server was specified.")

    # ensure user provided proper credentials
    if args.username is None:
        args.username = getpass.getuser()
    if args.password is None:
        if not args.force:
            # Prompt user to enter password interactively
            args.password = getpass.getpass("Password for {0}@{1}: "
                                            .format(args.username, args.server))
        else:
            p_deploy.error("No password specified for {0}@{1}"
                           .format(args.username, args.server))

    target = "vi://" + args.username + ":" + args.password + "@" + args.server

    with VMContextManager(args.PACKAGE, None) as vm:
        # ensure configuration was specified
        # will use ovf tool --deploymentOption
        # if not specified and force not specified prompt for selection
        profile_list = vm.get_configuration_profile_ids()

        if (args.configuration is not None and
            not (args.configuration in profile_list)):
            p_deploy.error("Configuration '{0}' is not a recognized profile "
                           "for '{1}'. Valid options are:\n{2}"
                           .format(args.configuration,
                                   args.PACKAGE,
                                   "\n".join(profile_list)))

        if profile_list and args.configuration is None:
            if len(profile_list) == 1:
                # No need to prompt the user
                args.configuration = profile_list[0]
                logger.debug("Auto-selected only profile '{0}'"
                             .format(args.configuration))
            elif args.force:
                args.configuration = vm.get_default_profile_name()
                logger.warning("Auto-selecting default profile '{0}'"
                               .format(args.configuration))
            profile_info_string = None
            while args.configuration is None:
                if not profile_info_string:
                    profile_info_string = vm.profile_info_string(enumerate=True)
                print(profile_info_string)
                user_input = get_input("Choose a Configuration:", "0")
                if user_input in profile_list:
                    args.configuration = user_input
                else:
                    try:
                        i = int(user_input)
                        if i >= len(profile_list):
                            raise ValueError
                        args.configuration = profile_list[i]
                    except ValueError:
                        print("\nInvalid input. Please try again.")

        if args.configuration is not None:
            args.ovftool_args.append("--deploymentOption=" + args.configuration)

        # Get the number of serial ports in the OVA.
        # ovftool does not create serial ports when deploying to a VM,
        # so we'll have to fix this up manually later.
        serial_count = vm.get_serial_count([args.configuration])

    # pass network settings on to ovftool
    if args.network_map is not None:
        for network in args.network_map:
            args.ovftool_args.append("--net:" + network)

    # check if user entered a name for the VM
    if args.vm_name is not None:
        args.ovftool_args.append("--name=" + args.vm_name)

    # tell ovftool to power on the VM
    # TODO - if serial port fixup (below) is implemented,
    # do not power on VM until after serial ports are added.
    if args.power_on:
        args.ovftool_args.append("--powerOn")

    # add package and target to the list
    args.ovftool_args.append(args.PACKAGE)
    args.ovftool_args.append(target)

    logger.debug("Final args to pass to OVFtool: {0}".format(args.ovftool_args))

    # Create new list with 'ovftool' at front
    new_list = ['ovftool'] + args.ovftool_args

    # use the new list to call ovftool
    print("Deploying VM...")
    check_output(new_list)
    print("VM has been deployed successfully.")

    # Post-fix of serial ports (ovftool will not implement)
    if serial_count > 0:
        # TODO - fixup not implemented yet
        # add serial ports as requested
        # power on VM if args.power_on
        logger.warning("Package '{0}' contains {1} serial ports, but ovftool "
                       "ignores serial port declarations. If these ports are "
                       "needed, you must add them manually to the new VM."
                       .format(args.PACKAGE, serial_count))


# Add ourselves to the parser options
p_deploy = subparsers.add_parser(
    'deploy', add_help=False,
    usage=("""
   {0} deploy --help
   {0} [-f] [-v] deploy [-c CONFIGURATION] [-n VM_NAME] [-N FROM=to] [-P]
                        [-u USERNAME] [-p PASSWORD] [-s SERVER]
                        HYPERVISOR PACKAGE [ovftool_args ...]"""
                .format(os.path.basename(sys.argv[0]))),
           help="""Create a new VM on the target hypervisor from the given OVF""",
           formatter_class=argparse.RawDescriptionHelpFormatter,
           description="""Deploy a virtual machine to a specified server.""",
           epilog=textwrap.dedent("""Examples:
   {0} deploy -u admin -p admin -s 192.0.2.100 esxi foo.ova
   {0} deploy -s 192.0.2.100 -n test_vm esxi foo.ova -o
   {0} deploy -u admin -s 192.0.2.100 -c 1CPU-2.5GB esxi foo.ova
   {0} deploy -u admin -s 192.0.2.100 -N 'GigabitEthernet1=VM Network'
   {0} deploy -u admin -s 192.0.2.100 esxi foo.ova --overwrite
   {0} -f deploy -u admin -p admin -s 192.0.2.100 esxi foo.ova
   {0} deploy -s 192.0.2.100 esxi foo.ova -ds=datastore1"""
                .format(os.path.basename(sys.argv[0]))))

subparser_lookup['deploy'] = p_deploy

p_deploy.add_argument('HYPERVISOR', choices=['esxi'],
                       help="""The hypervisor to be used""")
p_deploy.add_argument('PACKAGE', help="""OVF descriptor or OVA file""")

p_ds_gen = p_deploy.add_argument_group("General options")
p_ds_gen.add_argument('-h', '--help', action='help',
                      help="""Show this help message and exit""")

p_ds_config = p_deploy.add_argument_group("Configuration options")
p_ds_config.add_argument('-c', '--configuration',
                          help="""Use the specified configuration (as defined in
                                  the OVF). If unspecified the user will be
                                  prompted or the default configuration will be
                                  used.""")

p_ds_info = p_deploy.add_argument_group("VM info")
p_ds_info.add_argument('-n', '--vm-name',
                        help="""Name to use for the VM (if applicable) and any
                                files created. If unspecified, the name of the
                                OVF will be used.""")
p_ds_info.add_argument('-N', '--network-map', action='append',
                        help="""Map networks named in the OVF to networks
                                (bridges, vSwitches, etc.) in the hypervisor
                                environment. Syntax should be as follows:
                                -N <OVF name>=<target name>""")
p_ds_info.add_argument('-P', '--power-on', action='store_true',
                        help="""Power on the created VM to begin booting
                                immediately.""")

p_ds_cred = p_deploy.add_argument_group("Target info")
p_ds_cred.add_argument('-u', '--username',
                        help="""Username to log into the server that will
                                run this VM""")
p_ds_cred.add_argument('-p', '--password',
                        help="""Password to log into the server that will
                                run this VM""")
p_ds_cred.add_argument('-s', '--server',
                        help="""Server (IP address or URL) to run the VM
                                on (default: localhost)""")

p_ds_opt = p_deploy.add_argument_group("Optional arguments")
p_ds_opt.add_argument('ovftool_args', nargs=argparse.REMAINDER,
                       help="""Additional optional arguments to be sent to
                               ovftool""")

p_deploy.set_defaults(func=deploy)
