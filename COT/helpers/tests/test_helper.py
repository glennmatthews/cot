#!/usr/bin/env python
#
# test_helpers.py - Unit test cases for COT.helpers submodule.
#
# February 2015, Glenn F. Matthews
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

"""Unit test cases for the COT.helpers package."""

import contextlib
import os
import logging
import subprocess
from distutils.version import StrictVersion

import requests
import mock

from COT.ui import UI
from COT.tests import COTTestCase
from COT.helpers.helper import TemporaryDirectory, check_call, check_output
from COT.helpers import (
    Helper, PackageManager,
    HelperError, HelperNotFoundError,
    helpers, helper_select
)
from COT.helpers.port import Port
from COT.helpers.apt_get import AptGet

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc,protected-access


class HelperTestCase(COTTestCase):
    """Generic class for testing Helper and subclasses thereof."""

    def __init__(self, method_name='runTest'):
        """Add helper instance variable to generic UT initialization.

        For the parameters, see :class:`unittest.TestCase`.
        """
        self.helper = None
        super(HelperTestCase, self).__init__(method_name)

    def assertSubprocessCalls(self, mock_function, args_list):  # noqa: N802
        """Assert the mock_function was called with the given lists of args."""
        self.assertEqual(args_list,
                         # mock_function.call_args_list is a list of calls.
                         # A call is a tuple (args, kwargs)
                         # call_args_list[i] is the ith call to the mock,
                         # call_args_list[i][0] is the args for the ith call,
                         # and for the subprocess.check_[call|output] methods
                         # we are testing here,
                         # call_args_list[i][0][0] is the ith subprocess args.
                         [a[0][0] for a in mock_function.call_args_list],
                         "\nExpected: {0}\nGot:      {1}".format(
                             args_list,
                             [a[0][0] for a in mock_function.call_args_list]))

    def set_helper_version(self, ver):
        """Override the version number of the helper class."""
        self.helper._version = ver

    @staticmethod
    def select_package_manager(name):
        """Select the specified installer program for Helper to use."""
        for pm_name in ['apt-get', 'brew', 'port', 'yum']:
            helpers[pm_name]._installed = (pm_name == name)

    def enable_apt_install(self):
        """Set flags and values to force an apt-get update and apt install."""
        self.select_package_manager('apt-get')
        AptGet._updated = False
        os.environ['PREFIX'] = '/usr/local'
        if 'DESTDIR' in os.environ:
            del os.environ['DESTDIR']

    def enable_yum_install(self):
        """Set flags and values to force a yum install."""
        self.select_package_manager('yum')
        os.environ['PREFIX'] = '/usr/local'
        if 'DESTDIR' in os.environ:
            del os.environ['DESTDIR']

    def assertAptUpdated(self):  # noqa: N802
        """Assert that the hidden AptGet._updated flag is set."""
        self.assertTrue(AptGet._updated)

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def apt_install_test(self, pkgname, helpername, *_):
        """Test installation with 'dpkg' and 'apt-get'.

        Args:
          pkgname (str): Apt package to test installation for.
          helpername (str): Expected value of
              :attr:`~COT.helpers.helper.Helper.name`, if different from
              ``pkgname``.
        """
        helpers['dpkg']._installed = True
        with mock.patch.object(self.helper, '_path') as mock_path, \
            mock.patch('subprocess.check_call') as mock_check_call, \
            mock.patch('COT.helpers.helper.check_output',
                       return_value="is not installed and no "
                       "information is available") as mock_check_output:
            mock_path.return_value = (None, '/bin/' + helpername)
            self.enable_apt_install()
            self.helper.install()
            self.assertSubprocessCalls(mock_check_output,
                                       [['dpkg', '-s', pkgname]])
            self.assertSubprocessCalls(
                mock_check_call,
                [
                    ['apt-get', '-q', 'update'],
                    ['apt-get', '-q', 'install', pkgname],
                ])
            self.assertEqual(helpername, self.helper.name)
            self.assertAptUpdated()
            # Make sure we don't 'apt-get update' again unnecessarily
            mock_check_call.reset_mock()
            mock_check_output.reset_mock()
            self.helper.install()
            self.assertSubprocessCalls(mock_check_output,
                                       [['dpkg', '-s', pkgname]])
            self.assertSubprocessCalls(
                mock_check_call,
                [['apt-get', '-q', 'install', pkgname]])

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def brew_install_test(self, brew_params, *_):
        """Test installation with 'brew'.

        Args:
          brew_params (str,): Homebrew formula name to test, or list of args.
        """
        self.select_package_manager('brew')
        if isinstance(brew_params, str):
            brew_params = [brew_params]
        with mock.patch('subprocess.check_call') as mock_check_call, \
                mock.patch.object(self.helper, '_path') as mock_path:
            mock_path.return_value = (None, '/bin/' + brew_params[0])
            self.helper.install()
            mock_check_call.assert_called_with(
                ['brew', 'install'] + brew_params)

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def port_install_test(self, portname, *_):
        """Test installation with 'port'.

        Args:
          portname (str): MacPorts package name to test.
        """
        self.select_package_manager('port')
        Port._updated = False
        with mock.patch('subprocess.check_call') as mock_check_call, \
                mock.patch.object(self.helper, '_path') as mock_path:
            mock_path.return_value = (None, '/bin/' + portname)
            self.helper.install()
            self.assertSubprocessCalls(
                mock_check_call,
                [['port', 'selfupdate'],
                 ['port', 'install', portname]])
            self.assertTrue(Port._updated)
            # Make sure we don't call port selfupdate again unnecessarily
            mock_check_call.reset_mock()
            self.helper.install()
            self.assertSubprocessCalls(
                mock_check_call,
                [['port', 'install', portname]])

    def yum_install_test(self, pkgname, *_):
        """Test installation with yum."""
        self.enable_yum_install()
        self.helper._installed = False
        with mock.patch('subprocess.check_call') as mock_check_call:
            self.helper.install()
            mock_check_call.assert_called_with(
                ['yum', '--quiet', 'install', pkgname])

    @staticmethod
    @contextlib.contextmanager
    def stub_download_and_expand_tgz(_url):
        """Stub for Helper.download_and_expand_tgz - make a fake directory."""
        with TemporaryDirectory(prefix="cot_ut_helper") as directory:
            yield directory

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        # subclass needs to set self.helper
        super(HelperTestCase, self).setUp()
        if self.helper:
            self.helper._path = None
            self.helper._installed = False

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        for helper in helpers.values():
            helper._installed = None
            helper._path = None
            helper._version = None
        super(HelperTestCase, self).tearDown()

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    @mock.patch('platform.system', return_value='Windows')
    def test_install_windows_unsupported(self, *_):
        """No support for installation on Windows.

        This is a somewhat artificial test of logic in ``_install``
        that is normally unreachable when calling ``install()``.
        """
        if self.helper is None:
            return
        self.select_package_manager(None)
        self.assertRaises(NotImplementedError, self.helper._install)

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    @mock.patch('platform.system', return_value='Linux')
    def test_install_linux_no_package_manager(self, *_):
        """Unable to install on Linux without a package manager."""
        if self.helper is None:
            return
        self.select_package_manager(None)
        self.assertRaises(RuntimeError, self.helper._install)


class HelperGenericTest(HelperTestCase):
    """Test cases for generic Helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = Helper("generic")
        super(HelperGenericTest, self).setUp()

    def tearDown(self):
        """Cleanup function called automatically prior to each test."""
        self.helper._installed = False
        Helper._provider_package = {}
        super(HelperGenericTest, self).tearDown()

    def test_check_call_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist."""
        self.assertRaises(HelperNotFoundError,
                          check_call, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          check_call,
                          ["not_a_command"], require_success=True)

    def test_check_call_helpererror(self):
        """HelperError if executable fails and require_success is set."""
        with self.assertRaises(HelperError) as catcher:
            check_call(["false"])
        self.assertEqual(catcher.exception.errno, 1)

        check_call(["false"], require_success=False)

    @mock.patch('subprocess.check_call')
    def test_check_call_permissions_needed(self, mock_check_call):
        """Test cases where sudo permission is needed."""
        def raise_oserror(args, **_):
            """Raise an OSError unless using 'sudo'."""
            if args[0] != 'sudo':
                raise OSError(13, 'permission denied')
            return
        mock_check_call.side_effect = raise_oserror

        # Without retry_on_sudo, we reraise the permissions error
        with self.assertRaises(OSError) as catcher:
            check_call(["false"])
        self.assertEqual(catcher.exception.errno, 13)
        mock_check_call.assert_called_once_with(["false"])

        # With retry_on_sudo, we retry.
        mock_check_call.reset_mock()
        check_call(["false"], retry_with_sudo=True)
        mock_check_call.assert_has_calls([
            mock.call(['false']),
            mock.call(['sudo', 'false']),
        ])

        # Now a variant - the subprocess call actually executed, but the
        # process exited with a non-zero exit code
        def raise_subprocess_error(args, **_):
            """Raise a CalledProcessError unless using 'sudo'."""
            if args[0] != 'sudo':
                raise subprocess.CalledProcessError(1, " ".join(args))
            return
        mock_check_call.reset_mock()
        mock_check_call.side_effect = raise_subprocess_error

        # Without retry_on_sudo, we reraise the permissions error
        with self.assertRaises(HelperError) as catcher:
            check_call(["false"])
        self.assertEqual(catcher.exception.errno, 1)
        mock_check_call.assert_called_once_with(["false"])

        # With retry_on_sudo, we retry.
        mock_check_call.reset_mock()
        check_call(["false"], retry_with_sudo=True)
        mock_check_call.assert_has_calls([
            mock.call(['false']),
            mock.call(['sudo', 'false']),
        ])

    def test_check_output_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist."""
        self.assertRaises(HelperNotFoundError,
                          check_output, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          check_output, ["not_a_command"],
                          require_success=True)

    def test_check_output_oserror(self):
        """OSError if requested command isn't an executable."""
        self.assertRaises(OSError,
                          check_output, self.input_ovf)

    def test_check_output_helpererror(self):
        """HelperError if executable fails and require_success is set."""
        with self.assertRaises(HelperError) as catcher:
            check_output(["false"])

        self.assertEqual(catcher.exception.errno, 1)

        check_output(["false"], require_success=False)

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def test_helper_not_found(self, *_):
        """Make sure helper.path is None if find_executable fails."""
        self.assertEqual(self.helper.path, None)

    @mock.patch('COT.helpers.Helper._install')
    def test_install_already_present(self, mock_install):
        """Make installation is not attempted unnecessarily."""
        self.helper._installed = True
        self.helper.install()
        mock_install.assert_not_called()

    @mock.patch('COT.helpers.Helper.installable',
                new_callable=mock.PropertyMock, return_value=True)
    def test_install_not_implemented(self, *_):
        """If installable lies, default _install method should fail cleanly."""
        self.helper._installed = False
        self.assertRaises(NotImplementedError, self.helper.install)

    @mock.patch('COT.helpers.Helper.installable',
                new_callable=mock.PropertyMock, return_value=True)
    @mock.patch('platform.system', return_value='Darwin')
    def test_install_missing_package_manager_mac(self, *_):
        """RuntimeError if Mac install supported but brew/port are absent."""
        self.helper._installed = False
        self.helper._provider_package['brew'] = 'install-me-with-brew'
        self.helper._provider_package['port'] = 'install-me-with-port'
        self.select_package_manager(None)
        with self.assertRaises(RuntimeError) as catcher:
            self.helper.install()
        msg = str(catcher.exception)
        self.assertRegex(msg, "Unsure how to install generic.")
        # Since both helpers are supported, we should see both messages
        self.assertRegex(msg, "COT can use Homebrew")
        self.assertRegex(msg, "COT can use MacPorts")

        del self.helper._provider_package['brew']
        with self.assertRaises(RuntimeError) as catcher:
            self.helper.install()
        msg = str(catcher.exception)
        self.assertRegex(msg, "Unsure how to install generic.")
        # Now we should only see the supported one
        self.assertNotRegex(msg, "COT can use Homebrew")
        self.assertRegex(msg, "COT can use MacPorts")

        del self.helper._provider_package['port']
        # Now we should fall back to NotImplementedError
        with self.assertRaises(NotImplementedError) as catcher:
            self.helper.install()
        msg = str(catcher.exception)
        self.assertRegex(msg, "Unsure how to install generic.")
        self.assertNotRegex(msg, "COT can use Homebrew")
        self.assertNotRegex(msg, "COT can use MacPorts")

        self.helper._provider_package['brew'] = 'install-me-with-brew'
        with self.assertRaises(RuntimeError) as catcher:
            self.helper.install()
        msg = str(catcher.exception)
        self.assertRegex(msg, "Unsure how to install generic.")
        # Now we should only see the supported one
        self.assertRegex(msg, "COT can use Homebrew")
        self.assertNotRegex(msg, "COT can use MacPorts")

    @mock.patch('COT.helpers.Helper._install')
    @mock.patch('COT.helpers.Helper.installable',
                new_callable=mock.PropertyMock, return_value=True)
    def test_install_bad_implementation(self, *_):
        """If custom _install() doesn't do its job, install() catches it."""
        self.assertRaises(HelperNotFoundError, self.helper.install)

    def test_call_install(self):
        """call will call install, which raises an error."""
        self.assertRaises(NotImplementedError,
                          self.helper.call, ["Hello!"])

    def test_call_no_install(self):
        """If not installed, and user declines, raise HelperNotFoundError."""
        _ui = Helper.USER_INTERFACE
        Helper.USER_INTERFACE = UI()
        Helper.USER_INTERFACE.default_confirm_response = False
        try:
            self.assertRaises(HelperNotFoundError,
                              self.helper.call, ["Hello!"])
        finally:
            Helper.USER_INTERFACE = _ui

    def test_download_and_expand_tgz(self):
        """Validate the download_and_expand_tgz() context_manager."""
        try:
            with self.helper.download_and_expand_tgz(
                "https://github.com/glennmatthews/cot/archive/master.tar.gz"
            ) as directory:
                self.assertTrue(os.path.exists(directory))
                self.assertTrue(os.path.exists(
                    os.path.join(directory, "cot-master")))
                self.assertTrue(os.path.exists(
                    os.path.join(directory, "cot-master", "COT")))
                self.assertTrue(os.path.exists(
                    os.path.join(directory, "cot-master", "COT", "tests")))
                self.assertTrue(os.path.exists(
                    os.path.join(directory, "cot-master", "COT", "tests",
                                 "ut.py")))
        except requests.exceptions.ConnectionError:
            # unable to connect to github - might be an isolated environment
            self.fail("ConnectionError when trying to download from GitHub")
        # Temporary directory should be cleaned up when done
        self.assertFalse(os.path.exists(directory))


class PackageManagerGenericTest(HelperTestCase):
    """Unit test for abstract PackageManager class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = PackageManager("generic")
        super(PackageManagerGenericTest, self).setUp()

    def test_install_package_abstract(self):
        """The install_package API is abstract."""
        self.assertRaises(NotImplementedError,
                          self.helper.install_package, "COT")


@mock.patch('COT.helpers.helper.check_call')
@mock.patch('os.makedirs')
@mock.patch('os.path.exists', return_value=False)
@mock.patch('os.path.isdir', return_value=False)
class TestHelperMkDir(COTTestCase):
    """Test cases for Helper.mkdir()."""

    def test_already_exists(self, mock_isdir, mock_exists,
                            mock_makedirs, mock_check_call):
        """Test case where the target directory already exists."""
        mock_isdir.return_value = True
        self.assertTrue(Helper.mkdir('/foo/bar'))
        mock_isdir.assert_called_with('/foo/bar')
        mock_exists.assert_not_called()
        mock_makedirs.assert_not_called()
        mock_check_call.assert_not_called()

    def test_not_directory(self, mock_isdir, mock_exists,
                           mock_makedirs, mock_check_call):
        """Test case where a file exists at the target path."""
        mock_exists.return_value = True
        self.assertRaises(RuntimeError, Helper.mkdir, '/foo/bar')
        mock_isdir.assert_called_with('/foo/bar')
        mock_exists.assert_called_with('/foo/bar')
        mock_makedirs.assert_not_called()
        mock_check_call.assert_not_called()

    def test_permission_ok(self, mock_isdir, mock_exists,
                           mock_makedirs, mock_check_call):
        """Successfully create directory with user permissions."""
        self.assertTrue(Helper.mkdir('/foo/bar'))
        mock_isdir.assert_called_with('/foo/bar')
        mock_exists.assert_called_with('/foo/bar')
        mock_makedirs.assert_called_with('/foo/bar', 493)  # 493 == 0o755
        mock_check_call.assert_not_called()

    def test_need_sudo(self, mock_isdir, mock_exists,
                       mock_makedirs, mock_check_call):
        """Directory creation needs sudo."""
        mock_makedirs.side_effect = OSError
        self.assertTrue(Helper.mkdir('/foo/bar'))
        mock_isdir.assert_called_with('/foo/bar')
        mock_exists.assert_called_with('/foo/bar')
        mock_makedirs.assert_called_with('/foo/bar', 493)  # 493 == 0o755
        mock_check_call.assert_called_with(
            ['sudo', 'mkdir', '-p', '--mode=755', '/foo/bar'])

    def test_nondefault_permissions(self, mock_isdir, mock_exists,
                                    mock_makedirs, mock_check_call):
        """Non-default permissions should be applied whether sudo or not."""
        # Non-sudo case
        self.assertTrue(Helper.mkdir('/foo/bar', 511))  # 511 == 0o777
        mock_isdir.assert_called_with('/foo/bar')
        mock_exists.assert_called_with('/foo/bar')
        mock_makedirs.assert_called_with('/foo/bar', 511)
        mock_check_call.assert_not_called()

        # Sudo case
        mock_makedirs.reset_mock()
        mock_makedirs.side_effect = OSError
        self.assertTrue(Helper.mkdir('/foo/bar', 511))  # 511 == 0o777
        mock_makedirs.assert_called_with('/foo/bar', 511)
        mock_check_call.assert_called_with(
            ['sudo', 'mkdir', '-p', '--mode=777', '/foo/bar'])


@mock.patch('COT.helpers.helper.check_call')
@mock.patch('shutil.copy')
class TestHelperCopyFile(COTTestCase):
    """Test cases for Helper.copy_file()."""

    def test_permission_ok(self, mock_copy, mock_check_call):
        """File copy succeeds with user permissions."""
        self.assertTrue(Helper.copy_file('/foo', '/bar'))
        mock_copy.assert_called_with('/foo', '/bar')
        mock_check_call.assert_not_called()

    def test_need_sudo(self, mock_copy, mock_check_call):
        """File copy needs sudo."""
        mock_copy.side_effect = OSError
        self.assertTrue(Helper.copy_file('/foo', '/bar'))
        mock_copy.assert_called_with('/foo', '/bar')
        mock_check_call.assert_called_with(['sudo', 'cp', '/foo', '/bar'])


class TestHelperSelect(COTTestCase):
    """Test cases for helper_select() API."""

    def setUp(self):
        """Fake out helper availability."""
        super(TestHelperSelect, self).setUp()
        helpers['qemu-img']._installed = True
        helpers['qemu-img']._version = StrictVersion("2.1.0")
        helpers['vmdktool']._installed = True
        helpers['vmdktool']._version = StrictVersion("1.4")
        helpers['fatdisk']._installed = False

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        for helper in helpers.values():
            helper._installed = None
            helper._path = None
            helper._version = None
        super(TestHelperSelect, self).tearDown()

    def test_select_name_only(self):
        """Select a helper from a list of names only."""
        helper = helper_select(['fatdisk', 'vmdktool', 'qemu-img'])
        self.assertEqual(helper, helpers['vmdktool'])

    def test_select_name_version(self):
        """Select a helper from a list of names and versions."""
        helper = helper_select([('fatdisk', '1.4'),       # not installed
                                ('vmdktool', '2.0'),      # version too low
                                ('qemu-img', '2.1.0'),    # just right
                                ])
        self.assertEqual(helper, helpers['qemu-img'])

    @mock.patch('COT.helpers.fatdisk.FatDisk.installable',
                new_callable=mock.PropertyMock, return_value=False)
    @mock.patch('COT.helpers.vmdktool.VMDKTool.installable',
                new_callable=mock.PropertyMock, return_value=True)
    @mock.patch('COT.helpers.vmdktool.VMDKTool.install')
    def test_select_install_name_only(self, mock_install, *_):
        """Select and install a helper from a list of names only."""
        helpers['vmdktool']._installed = False
        helpers['qemu-img']._installed = False
        helper = helper_select(['fatdisk', 'vmdktool', 'qemu-img'])
        self.assertEqual(helper, helpers['vmdktool'])
        mock_install.assert_called_once_with()

    @mock.patch('COT.helpers.fatdisk.FatDisk.installable',
                new_callable=mock.PropertyMock, return_value=False)
    @mock.patch('COT.helpers.vmdktool.VMDKTool.installable',
                new_callable=mock.PropertyMock, return_value=True)
    @mock.patch('COT.helpers.qemu_img.QEMUImg.installable',
                new_callable=mock.PropertyMock, return_value=True)
    @mock.patch('COT.helpers.qemu_img.QEMUImg.install')
    @mock.patch('COT.helpers.vmdktool.VMDKTool.install')
    def test_select_install_name_version(self,
                                         mock_install_v, mock_install_q, *_):
        """Select and install a helper from a list of names and versions."""
        helpers['vmdktool']._installed = False
        helpers['qemu-img']._installed = False
        helper = helper_select([('fatdisk', '1.4'),       # not installable
                                ('vmdktool', '2.0'),      # version too low
                                ('qemu-img', '2.1.0'),    # just right
                                ])
        self.assertEqual(helper, helpers['qemu-img'])
        mock_install_v.assert_called_once_with()
        mock_install_q.assert_called_once_with()
