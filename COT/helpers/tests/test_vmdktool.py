#!/usr/bin/env python
#
# test_vmdktool.py - Unit test cases for COT.helpers.vmdktool submodule.
#
# March 2015, Glenn F. Matthews
# Copyright (c) 2014-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for the COT.helpers.vmdktool submodule."""

import os
from distutils.version import StrictVersion

import mock

from COT.helpers.tests.test_helper import HelperTestCase
from COT.helpers.vmdktool import VMDKTool
from COT.helpers import helpers

# pylint: disable=missing-type-doc,missing-param-doc,protected-access


@mock.patch('COT.helpers.Helper.download_and_expand_tgz',
            side_effect=HelperTestCase.stub_download_and_expand_tgz)
class TestVMDKTool(HelperTestCase):
    """Test cases for VMDKTool helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = VMDKTool()
        super(TestVMDKTool, self).setUp()

    @mock.patch('COT.helpers.helper.check_output',
                return_value="vmdktool version 1.3")
    def test_get_version(self, *_):
        """Test .version getter logic."""
        self.helper._installed = True
        self.assertEqual(self.helper.version, StrictVersion("1.3"))

    @mock.patch('COT.helpers.helper.check_output')
    @mock.patch('subprocess.check_call')
    def test_install_already_present(self, mock_check_call,
                                     mock_check_output, *_):
        """Do nothing instead of re-installing."""
        self.helper._installed = True
        self.helper.install()
        mock_check_output.assert_not_called()
        mock_check_call.assert_not_called()

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('os.path.isdir', return_value=False)
    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('os.makedirs', side_effect=OSError)
    @mock.patch('distutils.spawn.find_executable')
    @mock.patch('COT.helpers.helper.check_output', return_value="")
    @mock.patch('subprocess.check_call')
    def test_install_helper_apt_get(self,
                                    mock_check_call,
                                    mock_check_output,
                                    *_):
        """Test installation via 'apt-get'."""
        self.enable_apt_install()
        helpers['dpkg']._installed = True
        helpers['make']._installed = False
        self.helper.install()
        self.assertSubprocessCalls(
            mock_check_output,
            [
                ['dpkg', '-s', 'make'],
                ['dpkg', '-s', 'zlib1g-dev'],
            ])
        self.assertSubprocessCalls(
            mock_check_call,
            [
                ['apt-get', '-q', 'update'],
                ['apt-get', '-q', 'install', 'make'],
                ['apt-get', '-q', 'install', 'zlib1g-dev'],
                ['make', 'CFLAGS="-D_GNU_SOURCE -g -O -pipe"'],
                ['sudo', 'mkdir', '-p', '-m', '755', '/usr/local/man/man8'],
                ['sudo', 'mkdir', '-p', '-m', '755', '/usr/local/bin'],
                ['make', 'install', 'PREFIX=/usr/local'],
            ])
        self.assertAptUpdated()

        # Make sure we don't 'apt-get update/install' again unnecessarily
        mock_check_call.reset_mock()
        mock_check_output.reset_mock()
        mock_check_output.return_value = 'install ok installed'
        # fakeout!
        self.helper._installed = False
        helpers['make']._installed = True

        os.environ['PREFIX'] = '/opt/local'
        os.environ['DESTDIR'] = '/home/cot'

        self.helper.install()
        self.assertSubprocessCalls(
            mock_check_output,
            [
                ['dpkg', '-s', 'zlib1g-dev'],
            ])
        self.assertSubprocessCalls(
            mock_check_call,
            [
                ['make', 'CFLAGS="-D_GNU_SOURCE -g -O -pipe"'],
                ['sudo', 'mkdir', '-p', '-m', '755',
                 '/home/cot/opt/local/man/man8'],
                ['sudo', 'mkdir', '-p', '-m', '755',
                 '/home/cot/opt/local/bin'],
                ['make', 'install', 'PREFIX=/opt/local', 'DESTDIR=/home/cot'],
            ])

    def test_install_helper_brew(self, *_):
        """Test installation via 'brew'."""
        self.brew_install_test('vmdktool')

    def test_install_helper_port(self, *_):
        """Test installation via 'port'."""
        self.port_install_test('vmdktool')

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('os.path.isdir', return_value=False)
    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('os.makedirs', side_effect=OSError)
    @mock.patch('distutils.spawn.find_executable')
    @mock.patch('subprocess.check_call')
    def test_install_helper_yum(self,
                                mock_check_call,
                                *_):
        """Test installation via 'yum'."""
        self.enable_yum_install()
        self.helper._installed = False
        helpers['make']._installed = False
        self.helper.install()
        self.assertSubprocessCalls(
            mock_check_call,
            [
                ['yum', '--quiet', 'install', 'make'],
                ['yum', '--quiet', 'install', 'zlib-devel'],
                ['make', 'CFLAGS="-D_GNU_SOURCE -g -O -pipe"'],
                ['sudo', 'mkdir', '-p', '-m', '755', '/usr/local/man/man8'],
                ['sudo', 'mkdir', '-p', '-m', '755', '/usr/local/bin'],
                ['make', 'install', 'PREFIX=/usr/local'],
            ])

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def test_install_helper_linux_need_make_no_package_manager(self, *_):
        """Linux installation requires yum or apt-get if 'make' missing."""
        self.select_package_manager(None)
        self.assertRaises(NotImplementedError, self.helper.install)

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('distutils.spawn.find_executable')
    def test_install_linux_need_compiler_no_package_manager(self,
                                                            mock_find_exec,
                                                            *_):
        """Linux installation needs some way to install 'zlib'."""
        self.select_package_manager(None)
        mock_find_exec.side_effect = [None, '/bin/make']
        self.assertRaises(NotImplementedError, self.helper.install)

    @mock.patch('platform.system', return_value='Darwin')
    @mock.patch('COT.helpers.vmdktool.VMDKTool.installable',
                new_callable=mock.PropertyMock, return_value=True)
    def test_install_helper_mac_no_package_manager(self, *_):
        """Mac installation requires port."""
        self.select_package_manager(None)
        self.assertRaises(RuntimeError, self.helper.install)
