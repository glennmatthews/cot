#!/usr/bin/env python
#
# fatdisk.py - Unit test cases for COT.helpers.fatdisk submodule.
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

"""Unit test cases for the COT.helpers.fatdisk module."""

import logging
import os
import re
from distutils.version import StrictVersion

import mock

from COT.helpers.tests.test_helper import HelperUT
from COT.helpers.fatdisk import FatDisk
from COT.helpers import helpers

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc,protected-access


@mock.patch('COT.helpers.fatdisk.FatDisk.download_and_expand_tgz',
            side_effect=HelperUT.stub_download_and_expand_tgz)
class TestFatDisk(HelperUT):
    """Test cases for FatDisk helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = FatDisk()
        self.maxDiff = None
        super(TestFatDisk, self).setUp()

    @mock.patch('COT.helpers.helper.check_output',
                return_value="fatdisk, version 1.0.0-beta")
    def test_get_version(self, *_):
        """Validate .version getter."""
        self.helper._installed = True
        self.assertEqual(StrictVersion("1.0.0"), self.helper.version)

    @mock.patch('COT.helpers.helper.check_output')
    @mock.patch('subprocess.check_call')
    def test_install_already_present(self,
                                     mock_check_call,
                                     mock_check_output,
                                     *_):
        """Trying to re-install is a no-op."""
        self.helper._installed = True
        self.helper.install()
        mock_check_output.assert_not_called()
        mock_check_call.assert_not_called()

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('os.path.isdir', return_value=False)
    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('os.makedirs', side_effect=OSError)
    @mock.patch('distutils.spawn.find_executable', return_value="/foo")
    @mock.patch('shutil.copy', return_value=True)
    @mock.patch('COT.helpers.helper.check_output', return_value="")
    @mock.patch('subprocess.check_call')
    def test_install_apt_get(self,
                             mock_check_call,
                             mock_check_output,
                             mock_copy,
                             *_):
        """Test installation via 'apt-get'."""
        self.enable_apt_install()
        helpers['dpkg']._installed = True
        for name in ['make', 'clang', 'gcc', 'g++']:
            helpers[name]._installed = False

        self.helper.install()
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
        # fakeout!
        helpers['make']._installed = False
        self.helper._installed = False

        os.environ['PREFIX'] = '/opt/local'
        os.environ['DESTDIR'] = '/home/cot'

        self.helper.install()
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

    def test_install_brew(self, *_):
        """Test installation via 'brew'."""
        self.brew_install_test(['glennmatthews/fatdisk/fatdisk', '--devel'])

    def test_install_port(self, *_):
        """Test installation via 'port'."""
        self.port_install_test('fatdisk')

    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('os.path.isdir', return_value=False)
    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('os.makedirs', side_effect=OSError)
    @mock.patch('distutils.spawn.find_executable', return_value='/foo')
    @mock.patch('shutil.copy', return_value=True)
    @mock.patch('subprocess.check_call')
    def test_install_yum(self,
                         mock_check_call,
                         mock_copy,
                         *_):
        """Test installation via 'yum'."""
        self.enable_yum_install()
        for name in ['make', 'clang', 'gcc', 'g++']:
            helpers[name]._installed = False

        self.helper.install()
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
    def test_install_linux_need_make_no_package_manager(self, *_):
        """Linux installation requires yum or apt-get if 'make' missing."""
        self.select_package_manager(None)
        for name in ['make', 'clang', 'gcc', 'g++']:
            helpers[name]._installed = False
        with self.assertRaises(NotImplementedError):
            self.helper.install()

    @staticmethod
    def _find_make_only(name):
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
        for name in ['clang', 'gcc', 'g++']:
            helpers[name]._installed = False
        mock_find_exec.side_effect = self._find_make_only
        with self.assertRaises(NotImplementedError):
            self.helper.install()

    @mock.patch('platform.system', return_value='Darwin')
    @mock.patch('COT.helpers.fatdisk.FatDisk.installable',
                new_callable=mock.PropertyMock, return_value=True)
    def test_install_helper_mac_no_package_manager(self, *_):
        """Mac installation requires port."""
        self.select_package_manager(None)
        self.assertRaises(RuntimeError, self.helper.install)
