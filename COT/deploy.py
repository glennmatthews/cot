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
import re
import shlex
import getpass

from distutils.version import StrictVersion

from .submodule import COTReadOnlySubmodule
from COT.helper_tools import check_call, get_ovftool_version

logger = logging.getLogger(__name__)


class COTDeploy(COTReadOnlySubmodule):
    def __init__(self, UI, arg_names=None):
        if arg_names is None:
            arg_names = []
        arg_names = [
            "PACKAGE",
            "HYPERVISOR",
            "configuration",
            "username",
            "password",
            "power_on",
            "vm_name",
            "network_map",
        ] + arg_names
        super(COTDeploy, self).__init__(UI, arg_names)
        self.args["power_on"] = False
        self.generic_parser = None
        self.parser = None
        self.subparsers = None

    def validate_arg(self, arg, value):
        """Check whether it's OK to set the given argument to the given value.
        Returns either (True, massaged_value) or (False, reason)"""
        valid, value_or_reason = super(COTDeploy, self).validate_arg(arg,
                                                                     value)
        if not valid or value_or_reason is None:
            return valid, value_or_reason
        value = value_or_reason

        if arg == "HYPERVISOR":
            if value != "esxi":
                return False, ("'{0}' is not a supported hypervisor"
                               .format(value))
        elif arg == 'configuration' and self.vm is not None:
            profiles = self.vm.get_configuration_profile_ids()
            if value is not None and not (value in profiles):
                return False, ("'Configuration '{0}' is not a recognized "
                               "profile for '{1}'.\nValid options are:\n{2}"
                               .format(value, self.get_value("PACKAGE"),
                                       "\n".join(profiles)))
        elif arg == 'power_on':
            if value is not True and value is not False:
                return False, "power_on accepts boolean values only"

        return valid, value

    def ready_to_run(self):
        """Are we ready to go?
        Returns the tuple (ready, reason)"""
        if self.get_value("HYPERVISOR") is None:
            return False, "HYPERVISOR is a mandatory argument"
        return super(COTDeploy, self).ready_to_run()

    def create_subparser(self, parent):
        import argparse

        # Create a generic parser with arguments to be shared by all
        self.generic_parser = argparse.ArgumentParser(add_help=False)

        self.generic_parser.add_argument('-u', '--username',
                                         help="Server login username")

        self.generic_parser.add_argument('-p', '--password',
                                         help="Server login password")

        self.generic_parser.add_argument(
            '-c', '--configuration',
            help="Use the specified configuration profile defined in the OVF. "
            "If unspecified and the OVF has multiple profiles, the user will "
            "be prompted or the default configuration will be used.")

        self.generic_parser.add_argument(
            '-n', '--vm-name',
            help="Name to use for the VM (if applicable) and any files "
            "created. If unspecified, the name of the OVF will be used.")

        self.generic_parser.add_argument(
            '-P', '--power-on', action='store_true',
            help="Power on the created VM to begin booting immediately.")

        self.generic_parser.add_argument(
            '-N', '--network-map', action='append', nargs='+',
            metavar=('OVF_NET1=HOST_NET1', 'OVF_NET2=HOST_NET2'),
            help="Map networks named in the OVF to networks (bridges, "
            "vSwitches, etc.) in the hypervisor environment. This argument "
            "may be repeated as needed to specify multiple mappings.")

        # Create 'cot deploy' parser
        self.parser = parent.add_parser(
            'deploy',
            usage=self.UI.fill_usage("deploy", [
                "PACKAGE esxi ...",
            ]),
            help="Create a new VM on the target hypervisor from the given OVF",
            description="""Deploy a virtual machine to a specified server.""")

        self.parser.add_argument('PACKAGE', help="OVF descriptor or OVA file")

        self.subparsers = self.parser.add_subparsers(
            prog="cot deploy",
            dest='HYPERVISOR',
            metavar='hypervisors supported:')

        self.parser.set_defaults(instance=self)
        return 'deploy', self.parser


class COTDeployESXi(COTDeploy):
    def __init__(self, UI):
        super(COTDeployESXi, self).__init__(
            UI,
            [
                "LOCATOR",
                "datastore",
                "ovftool_args",
            ])
        self.args["ovftool_args"] = []

    def ready_to_run(self):
        """Are we ready to go?
        Returns the tuple (ready, reason)"""
        if self.get_value("LOCATOR") is None:
            return False, "LOCATOR is a mandatory argument"
        return super(COTDeployESXi, self).ready_to_run()

    def run(self):
        super(COTDeployESXi, self).run()

        # ensure user provided proper credentials
        username = self.get_value("username")
        password = self.get_value("password")
        LOCATOR = self.get_value("LOCATOR")
        server = LOCATOR.split("/")[0]
        if username is None:
            username = getpass.getuser()
        if password is None:
            password = self.UI.get_password(username, server)

        target = "vi://" + username + ":" + password + "@" + LOCATOR

        ovftool_args = self.get_value("ovftool_args")
        # Use shlex to split ovftool_args but respect quoted whitespace
        if ovftool_args:
            ovftool_args = shlex.split(ovftool_args)
            logger.debug("ovftool_args split to: {0}".format(ovftool_args))
        else:
            ovftool_args = []

        PACKAGE = self.get_value("PACKAGE")
        configuration = self.get_value("configuration")

        vm = self.vm

        # If locator is a vCenter locator "<vCenter>/datacenter/host/<host>"
        # then environment properties will always be used.
        # Otherwise we may need to help and/or warn the user:
        if vm.get_property_array() and not re.search("/host/", LOCATOR):
            if get_ovftool_version() < StrictVersion("4.0.0"):
                self.UI.confirm_or_die(
                    "When deploying an OVF directly to a vSphere target "
                    "using ovftool prior to version 4.0.0, any OVF "
                    "environment properties will not be made available "
                    "to the new guest.\n"
                    "If your guest needs environment properties, please "
                    "either specify a vCenter target locator (such as "
                    "'<vCenter>/<datacenter>/host/<host>') "
                    "or upgrade to ovftool 4.0.0 or later.\n"
                    "Continue deployment without OVF environment?")
                logger.warning("deploying directly to vSphere and ovftool "
                               "version is too low to add injectOvfEnv "
                               "option. OVF environment properties will "
                               "be ignored.")
            elif not self.get_value("power_on"):
                self.UI.confirm_or_die(
                    "When deploying an OVF directly to a vSphere target, "
                    "OVF environment properties can only be made available to "
                    "the new guest if the guest is to be powered on "
                    "immediately.\n"
                    "If your guest needs environment properties, please "
                    "either specify the '--power-on'/'-P' option or provide "
                    "a vCenter target locator (such as "
                    "'<vCenter>/<datacenter>/host/<host>') "
                    "instead of a vSphere target.\n"
                    "Continue deployment without OVF environment?")
                logger.warning("deploying directly to vSphere but "
                               "--power-on is not requested. OVF "
                               "environment properties will be ignored.")
            else:
                logger.debug("Since ovftool version is sufficient and user "
                             "requested --power-on, adding ovftool args to "
                             "ensure passthru of OVF environment to guest.")
                ovftool_args.append("--X:injectOvfEnv")

        # ensure configuration was specified
        # will use ovf tool --deploymentOption
        # if not specified and force not specified prompt for selection
        profile_list = vm.get_configuration_profile_ids()

        if profile_list and configuration is None:
            if len(profile_list) == 1:
                # No need to prompt the user
                configuration = profile_list[0]
                logger.debug("Auto-selected only profile '{0}'"
                             .format(configuration))
            profile_info_string = None
            while configuration is None:
                if not profile_info_string:
                    profile_info_string = vm.profile_info_string(
                        enumerate=True)
                user_input = self.UI.get_input(
                    profile_info_string + "\nChoose a Configuration:", "0")
                if user_input in profile_list:
                    configuration = user_input
                else:
                    try:
                        i = int(user_input)
                        configuration = profile_list[i]
                    except (ValueError, IndexError):
                        # TODO this should be handled by the UI
                        print("\nInvalid input. Please try again.")

        if configuration is not None:
            ovftool_args.append("--deploymentOption=" + configuration)

        # Get the number of serial ports in the OVA.
        # ovftool does not create serial ports when deploying to a VM,
        # so we'll have to fix this up manually later.
        serial_count = vm.get_serial_count([configuration])
        serial_count = serial_count[configuration]

        # pass network settings on to ovftool
        network_map = self.get_value("network_map")
        if network_map is not None:
            for nm in network_map:
                ovftool_args.append("--net:" + nm)

        # check if user entered a name for the VM
        vm_name = self.get_value("vm_name")
        if vm_name is not None:
            ovftool_args.append("--name=" + vm_name)

        # tell ovftool to power on the VM
        # TODO - if serial port fixup (below) is implemented,
        # do not power on VM until after serial ports are added.
        if self.get_value("power_on"):
            ovftool_args.append("--powerOn")

        # specify target datastore
        datastore = self.get_value("datastore")
        if datastore:
            ovftool_args.append("--datastore=" + datastore)

        # add package and target to the list
        ovftool_args.append(PACKAGE)
        ovftool_args.append(target)

        logger.debug("Final args to pass to OVFtool: {0}".format(ovftool_args))

        # Create new list with 'ovftool' at front
        cmd = ['ovftool'] + ovftool_args

        # use the new list to call ovftool
        logger.info("Deploying VM...")
        check_call(cmd)

        # Post-fix of serial ports (ovftool will not implement)
        if serial_count > 0:
            # TODO - fixup not implemented yet
            # add serial ports as requested
            # power on VM if power_on
            logger.warning(
                "Package '{0}' contains {1} serial ports, but ovftool "
                "ignores serial port declarations. If these ports are "
                "needed, you must add them manually to the new VM."
                .format(PACKAGE, serial_count))

    def create_subparser(self, parent):
        super(COTDeployESXi, self).create_subparser(parent)

        import argparse
        # Create 'cot deploy ... esxi' parser
        p = self.subparsers.add_parser(
            'esxi', parents=[self.generic_parser],
            usage=self.UI.fill_usage("deploy PACKAGE esxi", [
                "LOCATOR [-u USERNAME] [-p PASSWORD] [-c CONFIGURATION] "
                "[-n VM_NAME] [-P] [-N OVF1=HOST1 [-N OVF2=HOST2 ...]] "
                "[-d DATASTORE] [-o=OVFTOOL_ARGS]",
            ]),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            help="Deploy to ESXi, vSphere, or vCenter",
            description="Deploy OVF/OVA to ESXi/vCenter/vSphere hypervisor",
            epilog=self.UI.fill_examples([
                ('cot deploy foo.ova esxi 192.0.2.100 -u admin -p admin'
                 ' -n test_vm',
                 "Deploy to vSphere/ESXi server 192.0.2.100 with credentials"
                 " admin/admin, creating a VM named 'test_vm' from foo.ova."),
                ('cot deploy foo.ova esxi 192.0.2.100 -u admin -c 1CPU-2.5GB',
                 "Deploy to vSphere/ESXi server 192.0.2.100, with username"
                 " admin (prompting the user to input a password at runtime),"
                 " creating a VM based on profile '1CPU-2.5GB' in foo.ova."),
                ('cot deploy foo.ova esxi "192.0.2.100/mydc/host/192.0.2.1"'
                 ' -u administrator -N "GigabitEthernet1=VM Network"'
                 ' -N "GigabitEthernet2=myvswitch"',
                 "Deploy to vSphere server 192.0.2.1 which belongs to"
                 " datacenter 'mydc' on vCenter server 192.0.2.100, and map"
                 " the two NIC networks to vSwitches. Note that in this case"
                 " -u specifies the vCenter login username."),
                ('cot deploy foo.ova esxi 192.0.2.100 -u admin -p password'
                 ' --ovftool-args="--overwrite --acceptAllEulas"',
                 "Deploy with passthrough arguments to ovftool.")
            ]))

        # ovftool uses '-ds' as shorthand for '--datastore', so let's allow it.
        p.add_argument("-d", "-ds", "--datastore",
                       help="ESXi datastore to use for the new VM")

        p.add_argument("-o", "--ovftool-args",
                       help="Quoted string describing additional CLI "
                       """parameters to pass through to "ovftool". Examples:"""
                       """ -o="--foo", --ovftool-args="--foo --bar" """)

        p.add_argument("LOCATOR",
                       help="vSphere target locator. Examples: "
                       '"192.0.2.100" (deploy directly to ESXi server), '
                       '"192.0.2.101/mydatacenter/host/192.0.2.100" '
                       '(deploy via vCenter server)')

        p.set_defaults(instance=self)
        return 'deploy', p
