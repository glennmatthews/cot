#!/usr/bin/env python
#
# deploy_esxi.py - test cases for the COTDeployESXi class and helpers
#
# August 2015, Glenn F. Matthews
# Copyright (c) 2013-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for the COT.deploy.COTDeployESXi class and helpers."""

import errno
import getpass
import logging
import mock
import re
import requests
import socket
import ssl

from pyVmomi import vim
from distutils.version import StrictVersion

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
import COT.deploy_esxi
from COT.deploy_esxi import COTDeployESXi
from COT.data_validation import InvalidInputError

logger = logging.getLogger(__name__)


class TestCOTDeployESXi(COT_UT):
    """Test cases for COTDeployESXi class."""

    # Some WARNING logger messages we may expect at various points:
    SERIAL_PORT_NOT_FIXED = {
        'levelname': 'WARNING',
        'msg': 'serial port.*will not be created or configured',
    }
    VSPHERE_ENV_WARNING = {
        'levelname': 'WARNING',
        'msg': "deploying.*vSphere.*power-on.*environment properties.*ignored",
    }
    OVFTOOL_VER_TOO_LOW = {
        'levelname': 'WARNING',
        'msg': "ovftool version is too low.*environment properties.*ignored",
    }
    BAD_CERTIFICATE = {
        'levelname': 'WARNING',
        'msg': "certificate verify failed",
    }
    SESSION_FAILED = {
        'levelname': 'ERROR',
        'msg': "Session failed",
    }

    def stub_check_call(self, argv, require_success=True):
        """Stub for check_call - capture calls to ovftool."""
        logger.info("stub_check_call({0}, {1})".format(argv, require_success))
        if argv[0] == 'ovftool':
            self.last_argv = argv
            logger.info("Caught ovftool invocation")
            return
        return self._check_call(argv, require_success)

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCOTDeployESXi, self).setUp()
        self.instance = COTDeployESXi(UI())
        self.instance.package = self.input_ovf
        self.instance.hypervisor = 'esxi'
        # Stub out all ovftool dependencies
        self._ovftool_path = self.instance.ovftool._path
        self._check_call = self.instance.ovftool._check_call
        self._ovftool_version = self.instance.ovftool._version
        self.instance.ovftool._path = "/fake/ovftool"
        self.instance.ovftool._check_call = self.stub_check_call
        self.instance.ovftool._version = StrictVersion("4.0.0")

        self.last_argv = []

    def tearDown(self):
        """Test case cleanup function called automatically."""
        # Remove our stub
        self.instance.ovftool._path = self._ovftool_path
        self.instance.ovftool._check_call = self._check_call
        self.instance.ovftool._version = self._ovftool_version
        super(TestCOTDeployESXi, self).tearDown()

    def test_not_ready_with_no_args(self):
        """Verify ready_to_run() is False without all mandatory args."""
        ready, reason = self.instance.ready_to_run()
        self.assertEqual(ready, False)
        self.assertTrue(re.search("LOCATOR.*mandatory", reason))
        self.assertRaises(InvalidInputError, self.instance.run)

        self.instance.locator = "localhost"
        self.instance.package = None
        ready, reason = self.instance.ready_to_run()
        self.assertEqual(ready, False)
        self.assertTrue(re.search("PACKAGE.*mandatory", reason))
        self.assertRaises(InvalidInputError, self.instance.run)

    def test_invalid_args(self):
        """Negative tests for various arguments."""
        with self.assertRaises(InvalidInputError):
            self.instance.configuration = ""
        with self.assertRaises(InvalidInputError):
            self.instance.configuration = "X"
        with self.assertRaises(InvalidInputError):
            self.instance.power_on = "frobozz"

    def test_ovftool_args_basic(self):
        """Test that ovftool is called with the basic arguments."""
        self.instance.locator = "localhost"
        self.instance.run()
        self.assertEqual([
            'ovftool',
            '--deploymentOption=4CPU-4GB-3NIC',    # default configuration
            '--name=input',
            self.input_ovf,
            'vi://{user}:passwd@localhost'.format(user=getpass.getuser())
        ], self.last_argv)
        self.assertLogged(**self.VSPHERE_ENV_WARNING)
        self.assertLogged(**self.SERIAL_PORT_NOT_FIXED)

    def test_ovftool_args_advanced(self):
        """Test that ovftool is called with more involved arguments."""
        self.instance.locator = "localhost/host/foo"
        self.instance.datastore = "datastore1"
        self.instance.configuration = "2CPU-2GB-1NIC"
        self.instance.vm_name = "myVM"
        self.instance.power_on = True
        self.instance.ovftool_args = "--overwrite --vService:'A B=C D'"
        self.instance.username = "u"
        self.instance.password = "p"
        self.instance.network_map = ["VM Network=VM Network"]

        self.instance.run()
        self.assertEqual([
            'ovftool',
            '--overwrite',
            '--vService:A B=C D',
            '--deploymentOption=2CPU-2GB-1NIC',
            '--net:VM Network=VM Network',
            '--name=myVM',
            '--powerOn',
            '--datastore=datastore1',
            self.input_ovf,
            'vi://u:p@localhost/host/foo',
        ], self.last_argv)
        self.assertLogged(**self.SERIAL_PORT_NOT_FIXED)

    def test_ovftool_vsphere_env_fixup(self):
        """Test fixup of environment when deploying directly to vSphere."""
        # With 4.0.0 (our default) and no power_on, there's no fixup.
        # This is tested by test_ovftool_args_basic() above.

        # With 4.0.0 and power_on, we fixup when deploying to vSphere:
        self.instance.locator = "vsphere"
        self.instance.power_on = True
        self.instance.run()
        self.assertEqual([
            'ovftool',
            '--X:injectOvfEnv',
            '--deploymentOption=4CPU-4GB-3NIC',     # default configuration
            '--name=input',
            '--powerOn',
            self.input_ovf,
            'vi://{user}:passwd@vsphere'.format(user=getpass.getuser()),
        ], self.last_argv)
        self.assertLogged(**self.SERIAL_PORT_NOT_FIXED)
        # Make sure we DON'T see the ENV_WARNING message
        self.logging_handler.assertNoLogsOver(logging.INFO)

        # With 4.0.0, we don't (need to) fixup when deploying to vCenter.
        # This is tested by test_ovftool_args_advanced() above.

        # With <4.0.0, we don't (can't) fixup, regardless.
        # Discard cached information and update the info that will be returned
        self.instance.ovftool._version = StrictVersion("3.5.0")
        self.instance.run()
        self.assertEqual([
            'ovftool',
            # Nope! #'--X:injectOvfEnv',
            '--deploymentOption=4CPU-4GB-3NIC',     # default configuration
            '--name=input',
            '--powerOn',
            self.input_ovf,
            'vi://{user}:passwd@vsphere'.format(user=getpass.getuser()),
        ], self.last_argv)
        self.assertLogged(**self.OVFTOOL_VER_TOO_LOW)
        self.assertLogged(**self.SERIAL_PORT_NOT_FIXED)

    def test_serial_fixup_connection_error(self):
        """Call fixup_serial_ports() to connect to an invalid host."""
        self.instance.locator = "localhost"
        self.instance.serial_connection = ['tcp::2222', 'tcp::2223']
        with self.assertRaises((requests.exceptions.ConnectionError,
                                socket.error)) as cm:
            self.instance.fixup_serial_ports(2)
        # In requests 2.7 and earlier, we get the errno,
        # while in requests 2.8+, it's munged into a string only
        if cm.exception.errno is not None:
            self.assertEqual(cm.exception.errno, errno.ECONNREFUSED)
        self.assertRegexpMatches(
            cm.exception.strerror,
            "(Error connecting to localhost:443: )?.*Connection refused")

    @mock.patch('pyVim.connect.__Login')
    @mock.patch('pyVim.connect.__FindSupportedVersion')
    def test_serial_fixup_stubbed(self, mock_fsv, mock_login):
        """Test fixup_serial_ports by mocking pyVmomi library."""
        self.instance.locator = "localhost"
        self.instance.vm_name = "mockery"

        mock_fsv.return_value = ['vim25']
        mock_si = mock.create_autospec(COT.deploy_esxi.vim.ServiceInstance)
        mock_login.return_value = (mock_si, None)

        mock_sic = mock.create_autospec(
            COT.deploy_esxi.vim.ServiceInstanceContent)
        mock_si.RetrieveContent.return_value = mock_sic
        mock_sic.rootFolder = 'vim.Folder:group-d1'

        mock_v = mock.create_autospec(COT.deploy_esxi.vim.ViewManager)
        mock_sic.viewManager = mock_v

        mock_cv = mock.create_autospec(COT.deploy_esxi.vim.view.ContainerView)
        mock_v.CreateContainerView.return_value = mock_cv

        mock_vm = mock.create_autospec(COT.deploy_esxi.vim.VirtualMachine)
        mock_vm.name = self.instance.vm_name
        mock_cv.view = [mock_vm]

        self.instance.serial_connection = ['tcp:localhost:2222',
                                           'tcp::2223,server',
                                           '/dev/ttyS0']
        self.instance.fixup_serial_ports(3)

        self.assertTrue(mock_vm.ReconfigVM_Task.called)
        args, kwargs = mock_vm.ReconfigVM_Task.call_args
        spec = kwargs['spec']
        self.assertEqual(3, len(spec.deviceChange))
        s1, s2, s3 = spec.deviceChange
        self.assertEqual('add', s1.operation)
        self.assertEqual('add', s2.operation)
        self.assertEqual('add', s3.operation)
        self.assertEqual('tcp://localhost:2222', s1.device.backing.serviceURI)
        self.assertEqual('client', s1.device.backing.direction)
        self.assertEqual('tcp://:2223', s2.device.backing.serviceURI)
        self.assertEqual('server', s2.device.backing.direction)
        self.assertEqual('/dev/ttyS0', s3.device.backing.deviceName)

        self.instance.serial_connection = [
            'file:/tmp/foo.txt,datastore=datastore1'
        ]
        self.assertRaises(NotImplementedError,
                          self.instance.fixup_serial_ports, 1)
        self.assertLogged(**self.SESSION_FAILED)

    @mock.patch('COT.deploy_esxi.SmartConnection.__enter__')
    def test_serial_fixup_SSL_failure(self, mock_parent):
        """Test SSL failure in pyVmomi.

        Only applicable to 2.7+ and 3.4+ that have the new certificate logic.
        """
        if hasattr(ssl, '_create_unverified_context'):
            mock_parent.side_effect = vim.fault.HostConnectFault(
                msg="certificate verify failed")
            self.instance.locator = "localhost"
            self.instance.serial_connection = ['tcp://localhost:2222']
            self.assertRaises(vim.fault.HostConnectFault,
                              self.instance.fixup_serial_ports, 1)
            self.assertLogged(**self.BAD_CERTIFICATE)
