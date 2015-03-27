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

"""Module for deploying VM descriptions to a hypervisor to instantiate VMs.

**Classes**

.. autosummary::
  :nosignatures:

  COTDeploy
  COTDeployESXi
"""

import logging
import re
import shlex
import getpass

from distutils.version import StrictVersion

from .submodule import COTReadOnlySubmodule
from .helpers.ovftool import OVFTool
from COT.data_validation import InvalidInputError

logger = logging.getLogger(__name__)


class COTDeploy(COTReadOnlySubmodule):

    """Semi-abstract class for submodules used to deploy a VM to a hypervisor.

    Provides some baseline parameters and input validation that are expected
    to be common across all concrete subclasses.

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`,
    :attr:`~COTReadOnlySubmodule.package`,

    Attributes:
    :attr:`generic_parser`,
    :attr:`parser`,
    :attr:`subparsers`,
    :attr:`hypervisor`,
    :attr:`configuration`,
    :attr:`username`,
    :attr:`password`,
    :attr:`power_on`,
    :attr:`vm_name`,
    :attr:`network_map`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTDeploy, self).__init__(UI)
        # User inputs
        self._hypervisor = None
        self._configuration = None
        self.username = None
        """Server login username."""
        self.password = None
        """Server login password."""
        self._power_on = False
        self.vm_name = None
        """Name of the created virtual machine"""
        self._network_map = None
        # Internal attributes
        self.generic_parser = None
        """Generic parser object providing args that most subclasses will use.

        Subclasses can call
        ``self.subparsers.add_parser(parents=[self.generic_parser])``
        to automatically inherit this set of args
        """
        self.subparsers = None
        """Subparser grouping for hypervisor-specific sub-subparsers.

        Subclasses should generally have their :func:`create_subparser`
        implementations create their sub-subparsers under :attr:`subparsers`
        and NOT under :attr:`parent`.
        """

    @property
    def hypervisor(self):
        """Hypervisor to deploy to.

        :raise: :exc:`InvalidInputError` if not a recognized value.
        """
        return self._hypervisor

    @hypervisor.setter
    def hypervisor(self, value):
        if value != "esxi":
            raise InvalidInputError("'{0}' is not a supported hypervisor"
                                    .format(value))
        self._hypervisor = value

    @property
    def configuration(self):
        """VM configuration profile to use for deployment.

        :raise: :exc:`InvalidInputError` if not a profile defined in the VM.
        """
        return self._configuration

    @configuration.setter
    def configuration(self, value):
        if self.vm is not None:
            profiles = self.vm.config_profiles
            if value is not None and not (value in profiles):
                raise InvalidInputError(
                    "'Configuration '{0}' is not a recognized "
                    "profile for '{1}'.\nValid options are:\n{2}"
                    .format(value, self.package, "\n".join(profiles)))
        self._configuration = value

    @property
    def power_on(self):
        """Whether to automatically power on the VM after deployment."""
        return self._power_on

    @power_on.setter
    def power_on(self, value):
        if value is not True and value is not False:
            raise InvalidInputError("power_on accepts boolean values only")
        self._power_on = value

    @property
    def network_map(self):
        """Mapping of network names to networks."""
        return self._network_map

    @network_map.setter
    def network_map(self, value):
        for key_value_pair in value:
            try:
                (k, v) = key_value_pair.split('=', 1)
                logger.debug("network_map: key {0} value {1}".format(k, v))
                if k == '' or v == '':
                    raise ValueError("message is irrelevant")
                # Don't store the split values for now, as ovftool actually
                # prefers exactly this 'key=value' format. Just validate.
                # TODO - check 'k' against the list of networks in the OVF?
            except ValueError:
                raise InvalidInputError("Invalid network map '{0}' - mapping "
                                        "must be in 'network=target' form."
                                        .format(key_value_pair))
        self._network_map = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.hypervisor is None:
            return False, "HYPERVISOR is a mandatory argument"
        return super(COTDeploy, self).ready_to_run()

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        .. note::
          Unlike most submodules, this one has subparsers of its own -
          ``'cot deploy PACKAGE <hypervisor>'`` so subclasses of this module
          should call ``super().create_subparser(parent, storage)`` (to create
          the main 'deploy' subparser if it doesn't already exist) then call
          ``self.subparsers.add_parser()`` to add their own sub-subparser.

        :param object parent: Subparser grouping object returned by
            :func:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
        import argparse

        if storage.get('deploy', None) is None:
            # Create 'cot deploy' parser
            p = parent.add_parser(
                'deploy',
                usage=self.UI.fill_usage("deploy", [
                    "PACKAGE esxi ...",
                ]),
                help="Create a new VM on the target hypervisor from the "
                "given OVF or OVA",
                description="Deploy an OVF or OVA to create a virtual machine "
                "on a specified server.")

            p.add_argument('PACKAGE', help="OVF descriptor or OVA file")

            self.subparsers = p.add_subparsers(
                prog="cot deploy",
                dest='HYPERVISOR',
                metavar='<hypervisor>',
                title="hypervisors")

            p.set_defaults(instance=self)
            storage['deploy'] = p
        else:
            # Unfortunately argparse doesn't readily expose the subparsers of
            # an existing parser. The below should be considered experimental!
            self.subparsers = next(action for
                                   action in storage['deploy']._actions if
                                   type(action).name == '_SubParsersAction')

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


class COTDeployESXi(COTDeploy):

    """Submodule for deploying VMs on ESXi and VMware vCenter/vSphere.

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`,
    :attr:`~COTReadOnlySubmodule.package`,
    :attr:`generic_parser`,
    :attr:`parser`,
    :attr:`subparsers`,
    :attr:`hypervisor`,
    :attr:`configuration`,
    :attr:`username`,
    :attr:`password`,
    :attr:`power_on`,
    :attr:`vm_name`,
    :attr:`network_map`

    Attributes:
    :attr:`locator`,
    :attr:`datastore`,
    :attr:`ovftool_args`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTDeployESXi, self).__init__(UI)
        self.locator = None
        """vSphere target locator."""
        self.datastore = None
        """ESXi datastore to deploy to."""
        self._ovftool_args = []

        self.ovftool = OVFTool()

    @property
    def ovftool_args(self):
        """List of CLI arguments to pass through to ``ovftool``."""
        return list(self._ovftool_args)

    @ovftool_args.setter
    def ovftool_args(self, value):
        # Use shlex to split ovftool_args but respect quoted whitespace
        self._ovftool_args = shlex.split(value)
        logger.debug("ovftool_args split to: {0}"
                     .format(self._ovftool_args))

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.locator is None:
            return False, "LOCATOR is a mandatory argument"
        return super(COTDeployESXi, self).ready_to_run()

    def run(self):
        """Do the actual work of this submodule - deploying to ESXi.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTDeployESXi, self).run()

        # ensure user provided proper credentials
        server = self.locator.split("/")[0]
        if self.username is None:
            self.username = getpass.getuser()
        if self.password is None:
            self.password = self.UI.get_password(self.username, server)

        target = ("vi://" + self.username + ":" + self.password +
                  "@" + self.locator)

        ovftool_args = self.ovftool_args

        configuration = self.configuration

        vm = self.vm

        # If locator is a vCenter locator "<vCenter>/datacenter/host/<host>"
        # then environment properties will always be used.
        # Otherwise we may need to help and/or warn the user:
        if vm.environment_properties and not re.search("/host/", self.locator):
            if self.ovftool.version < StrictVersion("4.0.0"):
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
            elif not self.power_on:
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
        profile_list = vm.config_profiles

        if profile_list and configuration is None:
            if len(profile_list) == 1:
                # No need to prompt the user
                configuration = profile_list[0]
                logger.debug("Auto-selected only profile '{0}'"
                             .format(configuration))
            else:
                header, profile_info_list = vm.profile_info_list(
                    self.UI.terminal_width - 1)
                # Correct for the indentation of the list:
                header = "\n".join(["  " + h for h in header.split("\n")])
                configuration = self.UI.choose_from_list(
                    header=header,
                    option_list=profile_list,
                    info_list=profile_info_list,
                    footer="Enter configuration name or number",
                    default_value=self.vm.default_config_profile)

        if configuration is not None:
            ovftool_args.append("--deploymentOption=" + configuration)

        # Get the number of serial ports in the OVA.
        # ovftool does not create serial ports when deploying to a VM,
        # so we'll have to fix this up manually later.
        serial_count = vm.get_serial_count([configuration])
        serial_count = serial_count[configuration]

        # pass network settings on to ovftool
        if self.network_map is not None:
            for nm in self.network_map:
                ovftool_args.append("--net:" + nm)

        # check if user entered a name for the VM
        if self.vm_name is not None:
            ovftool_args.append("--name=" + self.vm_name)

        # tell ovftool to power on the VM
        # TODO - if serial port fixup (below) is implemented,
        # do not power on VM until after serial ports are added.
        if self.power_on:
            ovftool_args.append("--powerOn")

        # specify target datastore
        if self.datastore is not None:
            ovftool_args.append("--datastore=" + self.datastore)

        # add package and target to the list
        ovftool_args.append(self.package)
        ovftool_args.append(target)

        logger.debug("Final args to pass to OVFtool: {0}".format(ovftool_args))

        logger.info("Deploying VM...")
        self.ovftool.call_helper(ovftool_args, capture_output=False)

        # Post-fix of serial ports (ovftool will not implement)
        if serial_count > 0:
            # TODO - fixup not implemented yet
            # add serial ports as requested
            # power on VM if power_on
            logger.warning(
                "Package '{0}' contains {1} serial ports, but ovftool "
                "ignores serial port declarations. If these ports are "
                "needed, you must add them manually to the new VM."
                .format(self.package, serial_count))

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        This will create the shared :attr:`~COTDeploy.parser` under
        :attr:`parent`, then create our own sub-subparser under
        :attr:`~COTDeploy.subparsers`.

        :param object parent: Subparser grouping object returned by
            :func:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
        super(COTDeployESXi, self).create_subparser(parent, storage)

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
                ("Deploy to vSphere/ESXi server 192.0.2.100 with credentials"
                 " admin/admin, creating a VM named 'test_vm' from foo.ova.",
                 'cot deploy foo.ova esxi 192.0.2.100 -u admin -p admin'
                 ' -n test_vm'),
                ("Deploy to vSphere/ESXi server 192.0.2.100, with username"
                 " admin (prompting the user to input a password at runtime),"
                 " creating a VM based on profile '1CPU-2.5GB' in foo.ova.",
                 'cot deploy foo.ova esxi 192.0.2.100 -u admin -c 1CPU-2.5GB'),
                ("Deploy to vSphere server 192.0.2.1 which belongs to"
                 " datacenter 'mydc' on vCenter server 192.0.2.100, and map"
                 " the two NIC networks to vSwitches. Note that in this case"
                 " -u specifies the vCenter login username.",
                 'cot deploy foo.ova esxi "192.0.2.100/mydc/host/192.0.2.1"'
                 ' -u administrator -N "GigabitEthernet1=VM Network"'
                 ' -N "GigabitEthernet2=myvswitch"'),
                ("Deploy with passthrough arguments to ovftool.",
                 'cot deploy foo.ova esxi 192.0.2.100 -u admin -p password'
                 ' --ovftool-args="--overwrite --acceptAllEulas"')
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
        storage['deploy-esxi'] = p
