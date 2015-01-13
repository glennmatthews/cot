#!/usr/bin/env python
#
# deploy.py - Implements "cot deploy" command
#
# June 2014, Kevin A. Keim
# Copyright (c) 2014-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

import logging
import os.path
import re
import shlex
import sys
import getpass

from distutils.version import StrictVersion

from .cli import subparsers, subparser_lookup, argparse
from .cli import get_input, confirm_or_die
from .vm_context_manager import VMContextManager
from .vm_description import VMDescription
from COT.helper_tools import check_call, get_ovftool_version
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
    server = args.LOCATOR.split("/")[0]
    # ensure user provided proper credentials
    if args.username is None:
        args.username = getpass.getuser()
    if args.password is None:
        if not args.force:
            # Prompt user to enter password interactively
            args.password = getpass.getpass("Password for {0}@{1}: "
                                            .format(args.username, server))
        else:
            p_deploy_esxi.error("No password specified for {0}@{1}"
                                .format(args.username, server))

    # Use shlex to split ovftool_args but respect quoted whitespace
    if args.ovftool_args:
        args.ovftool_args = shlex.split(args.ovftool_args)
        logger.debug("ovftool_args split to: {0}".format(args.ovftool_args))
    else:
        args.ovftool_args = []


    target = "vi://" + args.username + ":" + args.password + "@" + args.LOCATOR

    with VMContextManager(args.PACKAGE, None) as vm:
        # If the locator is a vCenter locator "<vCenter>/datacenter/host/<host>"
        # then environment properties will always be used. Otherwise we may need
        # to help and/or warn the user:
        if vm.get_property_keys() and not re.search("/host/", args.LOCATOR):
            if get_ovftool_version() < StrictVersion("4.0.0"):
                confirm_or_die("When deploying an OVF directly to a vSphere "
                               "target using ovftool prior to version 4.0.0, "
                               "any OVF environment properties will not be "
                               "made available to the new guest.\n"
                               "If your guest needs environment properties, "
                               "please either specify a vCenter target locator "
                               "(such as '<vCenter>/<datacenter>/host/<host>') "
                               "or upgrade to ovftool 4.0.0 or later.\n"
                               "Continue deployment without OVF environment?",
                               args.force)
                logger.warning("deploying directly to vSphere and ovftool "
                               "version is too low to add injectOvfEnv option. "
                               "OVF environment properties will be ignored.")
            elif not args.power_on:
                confirm_or_die("When deploying an OVF directly to a vSphere "
                               "target, OVF environment properties can only "
                               "be made available to the new guest if the "
                               "guest is to be powered on immediately.\n"
                               "If your guest needs environment properties, "
                               "please either specify the '--power-on'/'-P' "
                               "option or provide a vCenter target locator "
                               "(such as '<vCenter>/<datacenter>/host/<host>') "
                               "instead of a vSphere target.\n"
                               "Continue deployment without OVF environment?",
                               args.force)
                logger.warning("deploying directly to vSphere but --power-on "
                               "is not requested. "
                               "OVF environment properties will be ignored.")
            else:
                logger.debug("Since ovftool version is sufficient and user "
                             "requested --power-on, adding ovftool args to "
                             "ensure passthrough of OVF environment to guest.")
                args.ovftool_args.append("--X:injectOvfEnv")

        # ensure configuration was specified
        # will use ovf tool --deploymentOption
        # if not specified and force not specified prompt for selection
        profile_list = vm.get_configuration_profile_ids()

        if (args.configuration is not None and
            not (args.configuration in profile_list)):
            p_deploy_esxi.error("Configuration '{0}' is not a recognized "
                                "profile for '{1}'. Valid options are:\n{2}"
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
        serial_count = serial_count[args.configuration]

    # pass network settings on to ovftool
    if args.network_map is not None:
        # This is a list of lists because we use both "nargs" and "append".
        # Flatten it!
        args.network_map = [nm for l in args.network_map for nm in l]
        for nm in args.network_map:
            args.ovftool_args.append("--net:" + nm)

    # check if user entered a name for the VM
    if args.vm_name is not None:
        args.ovftool_args.append("--name=" + args.vm_name)

    # tell ovftool to power on the VM
    # TODO - if serial port fixup (below) is implemented,
    # do not power on VM until after serial ports are added.
    if args.power_on:
        args.ovftool_args.append("--powerOn")

    # specify target datastore
    if args.datastore:
        args.ovftool_args.append("--datastore=" + args.datastore)

    # add package and target to the list
    args.ovftool_args.append(args.PACKAGE)
    args.ovftool_args.append(target)

    logger.debug("Final args to pass to OVFtool: {0}".format(args.ovftool_args))

    # Create new list with 'ovftool' at front
    cmd = ['ovftool'] + args.ovftool_args

    # use the new list to call ovftool
    print("Deploying VM...")
    check_call(cmd)

    # Post-fix of serial ports (ovftool will not implement)
    if serial_count > 0:
        # TODO - fixup not implemented yet
        # add serial ports as requested
        # power on VM if args.power_on
        print("WARNING: Package '{0}' contains {1} serial ports, but ovftool "
              "ignores serial port declarations. If these ports are "
              "needed, you must add them manually to the new VM."
              .format(args.PACKAGE, serial_count))


# Create a generic parser with arguments to be shared by all hypervisor-specific
p_deploy_generic = argparse.ArgumentParser(add_help=False)

p_deploy_generic.add_argument('-u', '--username', help="Server login username")

p_deploy_generic.add_argument('-p', '--password', help="Server login password")

p_deploy_generic.add_argument('-c', '--configuration', help=
"Use the specified configuration profile defined in the OVF. "
"If unspecified and the OVF has multiple profiles, the user will be prompted "
"or the default configuration will be used.")

p_deploy_generic.add_argument('-n', '--vm-name', help=
"Name to use for the VM (if applicable) and any files created. "
"If unspecified, the name of the OVF will be used.")

p_deploy_generic.add_argument('-P', '--power-on', action='store_true', help=
"Power on the created VM to begin booting immediately.")

p_deploy_generic.add_argument('-N', '--network-map', action='append', nargs='+',
                              metavar=('OVF_NET1=HOST_NET1',
                                       'OVF_NET2=HOST_NET2'), help=
"Map networks named in the OVF to networks (bridges, vSwitches, etc.) in the "
"hypervisor environment. This argument may be repeated as needed to specify "
"multiple mappings.")

p_deploy_generic.set_defaults(func=deploy)

p_deploy = subparsers.add_parser(
    'deploy',
    help="""Create a new VM on the target hypervisor from the given OVF""",
    description="""Deploy a virtual machine to a specified server.""")

subparser_lookup['deploy'] = p_deploy

p_deploy.add_argument('PACKAGE', help="""OVF descriptor or OVA file""")

hypervisor_subparsers = p_deploy.add_subparsers(
    dest='HYPERVISOR', metavar='hypervisors supported:')

p_deploy.set_defaults(func=deploy)


p_deploy_esxi = hypervisor_subparsers.add_parser(
    'esxi', parents=[p_deploy_generic],
    usage=("""
  {0} deploy PACKAGE esxi --help
  {0} [-f] [-v] deploy PACKAGE esxi LOCATOR
                       [-u USERNAME] [-p PASSWORD]
                       [-c CONFIGURATION] [-n VM_NAME] [-P]
                       [-N OVF1=HOST1] [[-N OVF2=HOST2] ...]
                       [-d DATASTORE] [-o=OVFTOOL_ARGS]"""
           .format(os.path.basename(sys.argv[0]))),
    formatter_class=argparse.RawDescriptionHelpFormatter,
    help="Deploy to ESXi, vSphere, or vCenter",
    description="Deploy OVF/OVA to ESXi/vCenter/vSphere hypervisor",
    epilog=textwrap.dedent("""Examples:
  {0} deploy foo.ova esxi 192.0.2.100 -u admin -p admin -n test_vm
    Deploy to vSphere/ESXi server 192.0.2.100 with credentials admin/admin,
    creating a VM named 'test_vm' from foo.ova.

  {0} deploy foo.ova esxi 192.0.2.100 -u admin -c 1CPU-2.5GB
    Deploy to vSphere/ESXi server 192.0.2.100 with username admin (prompting
    the user to input the password at runtime) creating a VM based on the
    '1CPU-2.5GB' profile in foo.ova.

  {0} deploy foo.ova esxi "192.0.2.100/mydc/host/192.0.2.1" -u administrator \\
        -N 'GigabitEthernet1=VM Network' -N 'GigabitEthernet2=myvswitch'
    Deploy to vSphere server 192.0.2.1 which belongs to datacenter 'mydc' on
    vCenter server 192.0.2.100, and map the two NIC networks to vSwitches.
    Note that in this case -u specifies the vCenter login username.

  {0} deploy foo.ova esxi 192.0.2.100 -u admin -p password \\
        --ovftool-args="--overwrite --acceptAllEulas"
    Deploy with passthrough arguments to ovftool."""
                           .format(os.path.basename(sys.argv[0]))))

# ovftool uses '-ds' as shorthand for '--datastore', so let's provide that too.
p_deploy_esxi.add_argument("-d", "-ds", "--datastore", help=
"ESXi datastore to use for the new VM")

p_deploy_esxi.add_argument("-o", "--ovftool-args", help=
"Quoted string describing additional CLI parameters to pass through "
"""to "ovftool". Examples: -o="--foo", --ovftool-args="--foo --bar" """)

p_deploy_esxi.add_argument("LOCATOR", help=
"vSphere target locator. Examples: "
'"192.0.2.100" (deploy directly to ESXi server), '
'"192.0.2.101/mydatacenter/host/192.0.2.100" (deploy via vCenter server)')

p_deploy_esxi.set_defaults(func=deploy_esxi, subsubcommand="deploy-esxi")

subparser_lookup["deploy-esxi"] = p_deploy_esxi

p_deploy.usage="""
  {0} deploy --help
  {0} [-f] [-v] deploy PACKAGE esxi ...""".format(os.path.basename(sys.argv[0]))
