#!/usr/bin/env python
#
# test_helpers.py - Unit test cases for COT.helpers submodule.
#
# February 2015, Glenn F. Matthews
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

"""Unit test cases for the COT.helpers package."""

import contextlib
import os
import logging
import subprocess

import requests
import mock

from COT.tests.ut import COT_UT
from COT.helpers.api import TemporaryDirectory
from COT.helpers.helper import Helper
import COT.helpers
from COT.helpers import HelperError, HelperNotFoundError

logger = logging.getLogger(__name__)


class HelperUT(COT_UT):
    """Generic class for testing Helper and subclasses thereof."""

    # commonly seen logger message for helpers
    ALREADY_INSTALLED = {
        'levelname': 'WARNING',
        'msg': "Tried to install .* but it's already available .*",
    }

    def __init__(self, method_name='runTest'):
        """Add helper instance variable."""
        self.helper = None
        super(HelperUT, self).__init__(method_name)

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
                         [a[0][0] for a in mock_function.call_args_list])

    def set_helper_version(self, ver):
        """Override the version number of the helper class."""
        self.helper._version = ver      # pylint: disable=protected-access

    def select_package_manager(self, name):  # pylint: disable=no-self-use
        """Select the specified installer program for Helper to use."""
        for pm in Helper.PACKAGE_MANAGERS:
            Helper.PACKAGE_MANAGERS[pm] = (pm == name)

    def enable_apt_install(self):
        """Set flags and values to force an apt-get update and apt install."""
        self.select_package_manager('apt-get')
        Helper._apt_updated = False     # pylint: disable=protected-access
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
        """Assert that the hidden _apt_updated flag is set."""
        # pylint: disable=protected-access
        self.assertTrue(Helper._apt_updated)

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def apt_install_test(self, pkgname, helpername, *_):
        """Test installation with 'dpkg' and 'apt-get'."""
        # Python 2.6 doesn't let us do multiple mocks in one 'with'
        with mock.patch.object(self.helper, '_path', new=None):
            with mock.patch('subprocess.check_call') as mock_check_call:
                with mock.patch(
                        'COT.helpers.helper.Helper._check_output',
                        return_value="is not installed and no"
                        "information is available") as mock_check_output:
                    self.enable_apt_install()
                    self.helper.install_helper()
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
                    self.helper.install_helper()
                    self.assertSubprocessCalls(mock_check_output,
                                               [['dpkg', '-s', pkgname]])
                    self.assertSubprocessCalls(
                        mock_check_call,
                        [['apt-get', '-q', 'install', pkgname]])

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def port_install_test(self, portname, *_):
        """Test installation with 'port'."""
        # pylint: disable=protected-access
        self.select_package_manager('port')
        Helper._port_updated = False
        # Python 2.6 doesn't let us use multiple contexts in one 'with'
        with mock.patch('subprocess.check_call') as mock_check_call:
            with mock.patch.object(self.helper, '_path', new=None):
                self.helper.install_helper()
                self.assertSubprocessCalls(
                    mock_check_call,
                    [['port', 'selfupdate'],
                     ['port', 'install', portname]])
                self.assertTrue(Helper._port_updated)
                # Make sure we don't call port selfupdate again unnecessarily
                mock_check_call.reset_mock()
                self.helper.install_helper()
                self.assertSubprocessCalls(
                    mock_check_call,
                    [['port', 'install', portname]])

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def yum_install_test(self, pkgname, *_):
        """Test installation with yum."""
        self.enable_yum_install()
        with mock.patch('subprocess.check_call') as mock_check_call:
            with mock.patch.object(self.helper, '_path', new=None):
                self.helper.install_helper()
                mock_check_call.assert_called_with(
                    ['yum', '--quiet', 'install', pkgname])

    @staticmethod
    @contextlib.contextmanager
    def stub_download_and_expand(_url):
        """Stub for Helper.download_and_expand - create a fake directory."""
        with TemporaryDirectory(prefix="cot_ut_helper") as d:
            yield d

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        # subclass needs to set self.helper
        super(HelperUT, self).setUp()
        if self.helper:
            self.helper._path = None   # pylint: disable=protected-access
        # save some environment properties for sanity
        self._port = Helper.PACKAGE_MANAGERS['port']
        self._apt_get = Helper.PACKAGE_MANAGERS['apt-get']
        self._yum = Helper.PACKAGE_MANAGERS['yum']

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        Helper.PACKAGE_MANAGERS['port'] = self._port
        Helper.PACKAGE_MANAGERS['apt-get'] = self._apt_get
        Helper.PACKAGE_MANAGERS['yum'] = self._yum
        super(HelperUT, self).tearDown()

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    @mock.patch('platform.system', return_value='Windows')
    def test_install_helper_unsupported(self, *_):
        """Unable to install without a package manager."""
        self.select_package_manager(None)
        if self.helper:
            with mock.patch.object(self.helper, '_path', new=None):
                self.assertRaises(NotImplementedError,
                                  self.helper.install_helper)


class HelperGenericTest(HelperUT):
    """Test cases for generic Helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = Helper("generic")
        super(HelperGenericTest, self).setUp()

    def test_check_call_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist."""
        # pylint: disable=protected-access
        self.assertRaises(HelperNotFoundError,
                          Helper._check_call, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          Helper._check_call,
                          ["not_a_command"], require_success=True)

    def test_check_call_helpererror(self):
        """HelperError if executable fails and require_success is set."""
        # pylint: disable=protected-access
        with self.assertRaises(HelperError) as cm:
            Helper._check_call(["false"])
        self.assertEqual(cm.exception.errno, 1)

        Helper._check_call(["false"], require_success=False)

    @mock.patch('subprocess.check_call')
    def test_check_call_permissions_needed(self, mock_check_call):
        """Test cases where sudo permission is needed."""
        def raise_oserror(args, **_):
            """Raise an OSError unless using 'sudo'."""
            if args[0] != 'sudo':
                raise OSError(13, 'permission denied')
            return
        mock_check_call.side_effect = raise_oserror

        # pylint: disable=protected-access

        # Without retry_on_sudo, we reraise the permissions error
        with self.assertRaises(OSError) as cm:
            Helper._check_call(["false"])
        self.assertEqual(cm.exception.errno, 13)
        mock_check_call.assert_called_once_with(["false"])

        # With retry_on_sudo, we retry.
        mock_check_call.reset_mock()
        Helper._check_call(["false"], retry_with_sudo=True)
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
        with self.assertRaises(HelperError) as cm:
            Helper._check_call(["false"])
        self.assertEqual(cm.exception.errno, 1)
        mock_check_call.assert_called_once_with(["false"])

        # With retry_on_sudo, we retry.
        mock_check_call.reset_mock()
        Helper._check_call(["false"], retry_with_sudo=True)
        mock_check_call.assert_has_calls([
            mock.call(['false']),
            mock.call(['sudo', 'false']),
        ])

    def test_check_output_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist."""
        # pylint: disable=protected-access
        self.assertRaises(HelperNotFoundError,
                          Helper._check_output, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          Helper._check_output, ["not_a_command"],
                          require_success=True)

    def test_check_output_oserror(self):
        """OSError if requested command isn't an executable."""
        # pylint: disable=protected-access
        self.assertRaises(OSError,
                          Helper._check_output, self.input_ovf)

    def test_check_output_helpererror(self):
        """HelperError if executable fails and require_success is set."""
        # pylint: disable=protected-access
        with self.assertRaises(HelperError) as cm:
            Helper._check_output(["false"])

        self.assertEqual(cm.exception.errno, 1)

        Helper._check_output(["false"], require_success=False)

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    def test_helper_not_found(self, *_):
        """Make sure helper.path is None if find_executable fails."""
        self.assertEqual(self.helper.path, None)

    def test_install_helper_already_present(self):
        """Make sure a warning is logged when attempting to re-install."""
        self.helper._path = True        # pylint: disable=protected-access
        self.helper.install_helper()
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_call_helper_install(self):
        """call_helper will call install_helper, which raises an error."""
        self.assertRaises(NotImplementedError,
                          self.helper.call_helper, ["Hello!"])

    @mock.patch('COT.helpers.helper.Helper.confirm', return_value=False)
    def test_call_helper_no_install(self, *_):
        """If not installed, and user declines, raise HelperNotFoundError."""
        self.assertRaises(HelperNotFoundError,
                          self.helper.call_helper, ["Hello!"])

    def test_download_and_expand(self):
        """Validate the download_and_expand() context_manager."""
        try:
            with COT.helpers.download_and_expand(
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
