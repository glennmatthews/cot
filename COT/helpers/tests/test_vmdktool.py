#!/usr/bin/env python
#
# test_vmdktool.py - Unit test cases for COT.helpers.vmdktoolsubmodule.
#
# March 2015, Glenn F. Matthews
# Copyright (c) 2014-2016 the COT project developers.
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

from COT.helpers.tests.test_helper import HelperUT
from COT.helpers.vmdktool import VmdkTool


@mock.patch('COT.helpers.download_and_expand',
            side_effect=HelperUT.stub_download_and_expand)
class TestVmdkTool(HelperUT):
    """Test cases for VmdkTool helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = VmdkTool()
        super(TestVmdkTool, self).setUp()

    @mock.patch('COT.helpers.helper.Helper._check_output',
                return_value="vmdktool version 1.4")
    def test_get_version(self, *_):
        """Test .version getter logic."""
        self.assertEqual(StrictVersion("1.4"), self.helper.version)

    @mock.patch('COT.helpers.helper.Helper._check_output')
    @mock.patch('subprocess.check_call')
    def test_install_helper_already_present(self, mock_check_call,
                                            mock_check_output, *_):
        """Do nothing instead of re-installing."""
        self.helper.install_helper()
        mock_check_output.assert_not_called()
        mock_check_call.assert_not_called()
        self.assertLogged(**self.ALREADY_INSTALLED)

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('os.path.isdir', return_value=False)
    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('os.makedirs', side_effect=OSError)
    @mock.patch('distutils.spawn.find_executable')
    @mock.patch('COT.helpers.helper.Helper._check_output', return_value="")
    @mock.patch('subprocess.check_call')
    def test_install_helper_apt_get(self,
                                    mock_check_call,
                                    mock_check_output,
                                    mock_find_executable,
                                    *_):
        """Test installation via 'apt-get'."""
        self.enable_apt_install()
        mock_find_executable.side_effect = [
            None,  # 'vmdktool',
            None,  # 'make', pre-installation
            '/bin/make',   # post-installation
        ]
        self.helper.install_helper()
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
                ['sudo', 'mkdir', '-p', '--mode=755', '/usr/local/man/man8'],
                ['sudo', 'mkdir', '-p', '--mode=755', '/usr/local/bin'],
                ['make', 'install', 'PREFIX=/usr/local'],
            ])
        self.assertAptUpdated()

        # Make sure we don't 'apt-get update/install' again unnecessarily
        mock_check_call.reset_mock()
        mock_check_output.reset_mock()
        mock_find_executable.reset_mock()
        mock_check_output.return_value = 'install ok installed'
        mock_find_executable.side_effect = [
            None,  # vmdktool
            '/bin/make',
        ]
        os.environ['PREFIX'] = '/opt/local'
        os.environ['DESTDIR'] = '/home/cot'
        self.helper.install_helper()
        self.assertSubprocessCalls(
            mock_check_output,
            [
                ['dpkg', '-s', 'zlib1g-dev'],
            ])
        self.assertSubprocessCalls(
            mock_check_call,
            [
                ['make', 'CFLAGS="-D_GNU_SOURCE -g -O -pipe"'],
                ['sudo', 'mkdir', '-p', '--mode=755',
                 '/home/cot/opt/local/man/man8'],
                ['sudo', 'mkdir', '-p', '--mode=755',
                 '/home/cot/opt/local/bin'],
                ['make', 'install', 'PREFIX=/opt/local', 'DESTDIR=/home/cot'],
            ])

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
                                mock_find_executable,
                                *_):
        """Test installation via 'yum'."""
        self.enable_yum_install()
        mock_find_executable.side_effect = [
            None,  # 'vmdktool',
            None,  # 'make', pre-installation
            '/bin/make',   # post-installation
        ]
        self.helper.install_helper()
        self.assertSubprocessCalls(
            mock_check_call,
            [
                ['yum', '--quiet', 'install', 'make'],
                ['yum', '--quiet', 'install', 'zlib-devel'],
                ['make', 'CFLAGS="-D_GNU_SOURCE -g -O -pipe"'],
                ['sudo', 'mkdir', '-p', '--mode=755', '/usr/local/man/man8'],
                ['sudo', 'mkdir', '-p', '--mode=755', '/usr/local/bin'],
                ['make', 'install', 'PREFIX=/usr/local'],
            ])

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def test_install_helper_linux_need_make_no_package_manager(self, *_):
        """Linux installation requires yum or apt-get if 'make' missing."""
        self.select_package_manager(None)
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('distutils.spawn.find_executable')
    def test_install_linux_need_compiler_no_package_manager(self,
                                                            mock_find_exec,
                                                            *_):
        """Linux installation needs some way to install 'zlib'."""
        self.select_package_manager(None)
        mock_find_exec.side_effect = [None, '/bin/make']
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

    def test_convert_unsupported(self, *_):
        """Negative test - conversion to unsupported format/subformat."""
        with self.assertRaises(NotImplementedError):
            self.helper.convert_disk_image(self.blank_vmdk, self.temp_dir,
                                           'qcow2')
        with self.assertRaises(NotImplementedError):
            self.helper.convert_disk_image(self.blank_vmdk, self.temp_dir,
                                           'vmdk', 'monolithicSparse')
