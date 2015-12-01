#!/usr/bin/env python
#
# deploy_esxi.py - Implements "cot deploy ... esxi" command
#
# August 2015, Glenn F. Matthews
# Copyright (c) 2014-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

"""Module for deploying VMs to ESXi, vCenter, and vSphere.

**Classes**

.. autosummary::
  :nosignatures:

  COTDeployESXi
  SmarterConnection
  PyVmomiVMReconfigSpec

"""

import getpass
import logging
import os.path
import re
import requests
import shlex
import ssl

from distutils.version import StrictVersion
from pyVmomi import vim
from pyVim.connect import SmartConnection

from .data_validation import ValueUnsupportedError
from .deploy import COTDeploy
from .helpers.ovftool import OVFTool

logger = logging.getLogger(__name__)


class SmarterConnection(SmartConnection):
    """A smarter version of pyVmomi's SmartConnection context manager."""

    def __init__(self, UI, server, username, password, port=443):
        """Create a connection to the given server."""
        self.UI = UI
        self.server = server
        self.username = username
        self.password = password
        self.port = port
        super(SmarterConnection, self).__init__(host=server, user=username,
                                                pwd=password, port=port)

    def __enter__(self):
        """Establish a connection and use it as the context manager object.

        Unlike SmartConnection, this lets the user override SSL certificate
        validation failures and connect anyway. It also produces slightly
        more meaningful error messages on failure.
        """
        logger.verbose("Establishing connection to {0}:{1}..."
                       .format(self.server, self.port))
        try:
            return super(SmarterConnection, self).__enter__()
        except vim.fault.HostConnectFault as e:
            if not re.search("certificate verify failed", e.msg):
                raise e
            # Self-signed certificates are pretty common for ESXi servers
            logger.warning(e.msg)
            self.UI.confirm_or_die("SSL certificate for {0} is self-signed or "
                                   "otherwise not recognized as valid. "
                                   "Accept certificate anyway?"
                                   .format(self.server))
            _create_unverified_context = ssl._create_unverified_context
            ssl._create_default_https_context = _create_unverified_context
            return super(SmarterConnection, self).__enter__()
        except requests.exceptions.ConnectionError as e:
            # ConnectionError can wrap another internal error; let's unwrap it
            # so COT can log it more cleanly
            outer_e = e
            inner_message = None
            while e.errno is None:
                inner_e = None
                if hasattr(outer_e, 'reason'):
                    inner_e = outer_e.reason
                else:
                    for arg in outer_e.args:
                        if isinstance(arg, Exception):
                            inner_e = arg
                            break
                if inner_e is None:
                    break
                if hasattr(inner_e, 'strerror'):
                    inner_message = inner_e.strerror
                elif hasattr(inner_e, 'message'):
                    inner_message = inner_e.message
                else:
                    inner_message = inner_e.args[0]
                logger.debug("\nInner exception: {0}".format(inner_e))
                if hasattr(inner_e, 'errno') and inner_e.errno is not None:
                    e.errno = inner_e.errno
                    break
                outer_e = inner_e
            if e.strerror is None:
                e.strerror = ("Error connecting to {0}:{1}: {2}"
                              .format(self.server, self.port, inner_message))
            raise

    def __exit__(self, type, value, trace):
        """Disconnect from the server."""
        super(SmarterConnection, self).__exit__()
        if type is not None:
            logger.error("Session failed - {0}".format(value))
        # TODO - re-enable SSL certificate validation?


class PyVmomiVMReconfigSpec:
    """Context manager for reconfiguring an ESXi VM using PyVmomi."""

    def __init__(self, conn, vm_name):
        """Use the given name to look up a VM using the given connection."""
        self.vm = self.get_obj(conn, vim.VirtualMachine, vm_name)
        assert(self.vm)
        self.spec = vim.vm.ConfigSpec()

    def get_obj(self, conn, vimtype, name):
        """Look up an object by name."""
        obj = None
        content = conn.RetrieveContent()
        container = content.viewManager.CreateContainerView(
            content.rootFolder, [vimtype], True)
        for c in container.view:
            if c.name == name:
                obj = c
                break
        return obj

    def __enter__(self):
        """Use a ConfigSpec as the context manager object."""
        return self.spec

    def __exit__(self, type, value, trace):
        """If the block exited cleanly, apply the ConfigSpec to the VM."""
        # Did we exit cleanly?
        if type is None:
            logger.verbose("Reconfiguring VM...")
            self.vm.ReconfigVM_Task(spec=self.spec)


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
    :attr:`serial_connection`

    Attributes:
    :attr:`locator`,
    :attr:`datastore`,
    :attr:`ovftool_args`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTDeployESXi, self).__init__(UI)
        self.datastore = None
        """ESXi datastore to deploy to."""
        self.host = None
        """vSphere host to deploy to - set implicitly by self.locator."""
        self.server = None
        """vCenter server or vSphere host - set implicitly by self.locator."""
        self._locator = None
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

    @property
    def locator(self):
        """Target vSphere locator."""
        return self._locator

    @locator.setter
    def locator(self, value):
        self._locator = value
        self.server = value.split("/")[0]
        self.host = os.path.basename(value)
        logger.debug("locator {0} --> server {1} / host {2}"
                     .format(value, self.server, self.host))

    @COTDeploy.serial_connection.setter
    def serial_connection(self, value):
        """Override parent property setter to add ESXi validation."""
        if len(value) > 4:
            raise ValueUnsupportedError(
                'serial port connection list', value,
                'no more than 4 connections (ESXi limitation)')
        COTDeploy.serial_connection.fset(self, value)

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
        if self.username is None:
            self.username = getpass.getuser()
        if self.password is None:
            self.password = self.UI.get_password(self.username, self.server)

        target = ("vi://" + self.username + ":" + self.password +
                  "@" + self.locator)

        ovftool_args = self.ovftool_args

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

        if self.configuration is not None:
            ovftool_args.append("--deploymentOption=" + self.configuration)

        # Get the number of serial ports in the OVA.
        # ovftool does not create serial ports when deploying to a VM,
        # so we'll have to fix this up manually later.
        serial_count = vm.get_serial_count([self.configuration])
        serial_count = serial_count[self.configuration]

        # pass network settings on to ovftool
        if self.network_map is not None:
            for nm in self.network_map:
                ovftool_args.append("--net:" + nm)

        # check if user entered a name for the VM
        if self.vm_name is None:
            self.vm_name = os.path.splitext(os.path.basename(self.package))[0]
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
            # add serial ports as requested
            self.fixup_serial_ports(serial_count)
        # power on VM if power_on

    def fixup_serial_ports(self, serial_count):
        """Use PyVmomi to create and configure serial ports for the new VM."""
        if serial_count > len(self.serial_connection):
            logger.warning("No serial connectivity information is "
                           "available for {0} serial port(s) - "
                           "they will not be created or configured."
                           .format(serial_count -
                                   len(self.serial_connection)))

        if len(self.serial_connection) == 0:
            return

        logger.info("Fixing up serial ports...")
        with SmarterConnection(self.UI, self.server,
                               self.username, self.password) as conn:
            logger.verbose("Connection established")
            with PyVmomiVMReconfigSpec(conn, self.vm_name) as spec:
                logger.verbose("Spec created")
                spec.deviceChange = []
                # TODO - import backing info from OVF environment
                # TODO - prompt user for values if not in OVF and not specified
                for s in self.serial_connection:
                    logger.verbose(s)
                    serial_spec = vim.vm.device.VirtualDeviceSpec()
                    serial_spec.operation = 'add'
                    serial_port = vim.vm.device.VirtualSerialPort()
                    serial_port.yieldOnPoll = True

                    if s.kind == 'device':
                        backing = serial_port.DeviceBackingInfo()
                        logger.info("Serial port will use host device {0}"
                                    .format(s.value))
                        backing.deviceName = s.value
                    elif s.kind == 'telnet' or s.kind == 'tcp':
                        backing = serial_port.URIBackingInfo()
                        backing.serviceURI = s.kind + '://' + s.value
                        if 'server' in s.options:
                            logger.info("Serial port will be a {0} server "
                                        "at {1}"
                                        .format(s.kind, s.value))
                            backing.direction = 'server'
                        else:
                            logger.info("Serial port will connect via {0} "
                                        "to {1}. Use ',server' option if a "
                                        "server is desired instead of client."
                                        .format(s.kind, s.value))
                            backing.direction = 'client'
                    else:
                        # TODO - support other backing types
                        raise NotImplementedError("no support yet for '{0}'"
                                                  .format(s.kind))

                    serial_port.backing = backing
                    serial_spec.device = serial_port
                    spec.deviceChange.append(serial_spec)

        logger.info("Done with serial port fixup")

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
                "[-S CONN1 [-S CONN2 ...]] [-d DATASTORE] [-o=OVFTOOL_ARGS]",
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
                 " creating a VM based on profile '1CPU-2.5GB' in foo.ova,"
                 " and creating the serial port as a telnet server listening"
                 " on port 10022 of the host",
                 'cot deploy foo.ova esxi 192.0.2.100 -u admin -c 1CPU-2.5GB'
                 ' -S telnet://:10022,server'),
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
