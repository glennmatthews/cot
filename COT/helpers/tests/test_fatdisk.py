#!/usr/bin/env python
#
# fatdisk.py - Unit test cases for COT.helpers.fatdisk submodule.
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

"""Unit test cases for the COT.helpers.fatdisk module."""

import logging
import os
import re
from distutils.version import StrictVersion

import mock

from COT.helpers.tests.test_helper import HelperUT
from COT.helpers.fatdisk import FatDisk

logger = logging.getLogger(__name__)


@mock.patch('COT.helpers.download_and_expand',
            side_effect=HelperUT.stub_download_and_expand)
class TestFatDisk(HelperUT):
    """Test cases for FatDisk helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = FatDisk()
        self.maxDiff = None
        super(TestFatDisk, self).setUp()

    @mock.patch('COT.helpers.helper.Helper._check_output',
                return_value="fatdisk, version 1.0.0-beta")
    def test_get_version(self, *_):
        """Validate .version getter."""
        self.assertEqual(StrictVersion("1.0.0"), self.helper.version)

    @mock.patch('COT.helpers.helper.Helper._check_output')
    @mock.patch('subprocess.check_call')
    def test_install_helper_already_present(self, mock_check_call,
                                            mock_check_output, *_):
        """Trying to re-install is a no-op."""
        self.helper.install_helper()
        mock_check_output.assert_not_called()
        mock_check_call.assert_not_called()
        self.assertLogged(**self.ALREADY_INSTALLED)

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('os.path.isdir', return_value=False)
    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('os.makedirs', side_effect=OSError)
    @mock.patch('distutils.spawn.find_executable')
    @mock.patch('shutil.copy', return_value=True)
    @mock.patch('COT.helpers.helper.Helper._check_output', return_value="")
    @mock.patch('subprocess.check_call')
    def test_install_helper_apt_get(self,
                                    mock_check_call,
                                    mock_check_output,
                                    mock_copy,
                                    mock_find_executable,
                                    *_):
        """Test installation via 'apt-get'."""
        self.enable_apt_install()
        mock_find_executable.side_effect = [
            None,  # 'fatdisk',
            None,  # 'make', pre-installation
            '/bin/make',   # post-installation
            None,  # 'clang'
            None,  # 'gcc', pre-installation
            None,  # 'g++'
            '/bin/gcc',   # post-installation
        ]

        self.helper.install_helper()
        self.assertSubprocessCalls(
            mock_check_output,
            [
                ['dpkg', '-s', 'make'],
                ['dpkg', '-s', 'gcc'],
            ])
        self.assertSubprocessCalls(
            mock_check_call,
            [
                ['apt-get', '-q', 'update'],
                ['apt-get', '-q', 'install', 'make'],
                ['apt-get', '-q', 'install', 'gcc'],
                ['./RUNME'],
                ['sudo', 'mkdir', '-p', '--mode=755', '/usr/local/bin'],
            ])
        self.assertTrue(re.search("/fatdisk$", mock_copy.call_args[0][0]))
        self.assertEqual('/usr/local/bin', mock_copy.call_args[0][1])
        self.assertAptUpdated()

        # Make sure we don't call apt-get update/install again unnecessarily.
        mock_check_output.reset_mock()
        mock_check_call.reset_mock()
        mock_check_output.return_value = 'install ok installed'
        mock_find_executable.reset_mock()
        mock_find_executable.side_effect = [
            None,  # fatdisk
            None,  # fakeout make not here
            '/bin/make',   # actually it is here!
            '/bin/clang',
        ]
        os.environ['PREFIX'] = '/opt/local'
        os.environ['DESTDIR'] = '/home/cot'

        self.helper.install_helper()
        self.assertSubprocessCalls(
            mock_check_output,
            [
                ['dpkg', '-s', 'make'],
            ])
        self.assertSubprocessCalls(
            mock_check_call,
            [
                ['./RUNME'],
                ['sudo', 'mkdir', '-p', '--mode=755',
                 '/home/cot/opt/local/bin'],
            ])
        self.assertTrue(re.search("/fatdisk$", mock_copy.call_args[0][0]))
        self.assertEqual('/home/cot/opt/local/bin', mock_copy.call_args[0][1])

    def test_install_helper_port(self, *_):
        """Test installation via 'port'."""
        self.port_install_test('fatdisk')

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('os.path.isdir', return_value=False)
    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('os.makedirs', side_effect=OSError)
    @mock.patch('distutils.spawn.find_executable')
    @mock.patch('shutil.copy', return_value=True)
    @mock.patch('subprocess.check_call')
    def test_install_helper_yum(self,
                                mock_check_call,
                                mock_copy,
                                mock_find_executable,
                                *_):
        """Test installation via 'yum'."""
        self.enable_yum_install()
        mock_find_executable.side_effect = [
            None,  # vmdktool
            None,  # make, pre-installation
            '/bin/make',  # post-installation
            None,  # 'clang'
            None,  # 'gcc', pre-installation
            None,  # 'g++'
            '/bin/gcc',   # post-installation
        ]

        self.helper.install_helper()
        self.assertSubprocessCalls(
            mock_check_call,
            [
                ['yum', '--quiet', 'install', 'make'],
                ['yum', '--quiet', 'install', 'gcc'],
                ['./RUNME'],
                ['sudo', 'mkdir', '-p', '--mode=755', '/usr/local/bin'],
            ])
        self.assertTrue(re.search("/fatdisk$", mock_copy.call_args[0][0]))
        self.assertEqual('/usr/local/bin', mock_copy.call_args[0][1])

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def test_install_helper_linux_need_make_no_package_manager(self, *_):
        """Linux installation requires yum or apt-get if 'make' missing."""
        self.select_package_manager(None)
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()

    @staticmethod
    def _find_make_only(name):  # pylint: disable=no-self-use
        """Stub for distutils.spawn.find_executable - only finds 'make'."""
        logger.info("stub_find_executable(%s)", name)
        if name == 'make':
            return "/bin/make"
        else:
            return None

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('COT.helpers.helper.Helper')
    @mock.patch('distutils.spawn.find_executable')
    def test_install_linux_need_compiler_no_package_manager(self,
                                                            mock_find_exec,
                                                            *_):
        """Linux installation requires yum or apt-get if 'gcc' missing."""
        self.select_package_manager(None)
        mock_find_exec.side_effect = self._find_make_only
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()
