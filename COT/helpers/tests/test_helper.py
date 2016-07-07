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
import platform
import subprocess
from requests.exceptions import ConnectionError
import mock

from COT.tests.ut import COT_UT
from COT.helpers.helper import Helper
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

    def set_helper_version(self, ver):
        """Override the version number of the helper class."""
        self.helper._version = ver      # pylint: disable=protected-access

    def select_package_manager(self, name):
        """Select the specified installer program for Helper to use."""
        Helper.find_executable = self.stub_find_executable
        for pm in Helper.PACKAGE_MANAGERS.keys():
            Helper.PACKAGE_MANAGERS[pm] = (pm == name)

    def enable_apt_install(self):
        """Set flags and values to force an apt-get update and apt install."""
        self.select_package_manager('apt-get')
        Helper._apt_updated = False     # pylint: disable=protected-access
        self.fake_output = 'is not installed and no information is available'
        self.system = 'Linux'
        os.environ['PREFIX'] = '/usr/local'
        if 'DESTDIR' in os.environ:
            del os.environ['DESTDIR']

    def enable_yum_install(self):
        """Set flags and values to force a yum install."""
        self.select_package_manager('yum')
        self.system = 'Linux'
        os.environ['PREFIX'] = '/usr/local'
        if 'DESTDIR' in os.environ:
            del os.environ['DESTDIR']

    def assertAptUpdated(self):  # noqa: N802
        """Assert that the hidden _apt_updated flag is set."""
        # pylint: disable=protected-access
        self.assertTrue(Helper._apt_updated)

    def apt_install_test(self, pkgname, helpername=None):
        """Test installation with 'dpkg' and 'apt-get'."""
        self.enable_apt_install()
        self.helper.install_helper()
        self.assertEqual([
            ['dpkg', '-s', pkgname],
            ['apt-get', '-q', 'update'],
            ['apt-get', '-q', 'install', pkgname],
        ], self.last_argv)
        if not helpername:
            helpername = pkgname
        self.assertEqual(helpername, self.helper.name)
        self.assertAptUpdated()
        # Make sure we don't 'apt-get update' again unnecessarily
        self.last_argv = []
        self.helper.install_helper()
        self.assertEqual([
            ['dpkg', '-s', pkgname],
            ['apt-get', '-q', 'install', pkgname],
        ], self.last_argv)

    def port_install_test(self, portname):
        """Test installation with 'port'."""
        # pylint: disable=protected-access
        self.select_package_manager('port')
        Helper._port_updated = False
        self.helper.install_helper()
        self.assertEqual([['port', 'selfupdate'],
                          ['port', 'install', portname]],
                         self.last_argv)
        self.assertTrue(Helper._port_updated)
        # Make sure we don't call port selfupdate again unnecessarily
        self.last_argv = []
        self.helper.install_helper()
        self.assertEqual([['port', 'install', portname]],
                         self.last_argv)

    def stub_check_call(self, argv, require_success=True, **_kwargs):
        """Stub for Helper._check_call - store the argv and do nothing."""
        logger.info("stub_check_call(%s, %s)", argv, require_success)
        self.last_argv.append(argv)

    def stub_check_output(self, argv, require_success=True, **_kwargs):
        """Stub for Helper._check_output - return canned output."""
        logger.info("stub_check_output(%s, %s)", argv, require_success)
        self.last_argv.append(argv)
        if self.fake_output is not None:
            return self.fake_output
        return self._check_output(argv, require_success)

    def stub_find_executable(self, name):
        """Stub for Helper.find_executable - returns a fixed response."""
        logger.info("stub_find_executable(%s)", name)
        return self.fake_path

    @contextlib.contextmanager
    def stub_download_and_expand(self, _url):
        """Stub for Helper.download_and_expand - create a fake directory."""
        from COT.helpers.helper import TemporaryDirectory
        with TemporaryDirectory(prefix=("cot_ut_" + self.helper.name)) as d:
            yield d

    def stub_confirm(self, _prompt):
        """Stub for confirm() - return fixed response."""
        return self.default_confirm_response

    def stub_system(self):
        """Stub for platform.system() - return fixed platform string."""
        return self.system

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        # subclass needs to set self.helper
        super(HelperUT, self).setUp()
        self.fake_output = None
        self.fake_path = None
        self.last_argv = []
        # pylint: disable=protected-access
        self._check_call = Helper._check_call
        Helper._check_call = self.stub_check_call
        self._check_output = Helper._check_output
        Helper._check_output = self.stub_check_output
        self._download_and_expand = Helper.download_and_expand
        Helper.download_and_expand = self.stub_download_and_expand
        self.default_confirm_response = True
        self._confirm = Helper.confirm
        Helper.confirm = self.stub_confirm
        self._system = platform.system
        self.system = None
        platform.system = self.stub_system
        # save some environment properties for sanity
        self._port = Helper.PACKAGE_MANAGERS['port']
        self._apt_get = Helper.PACKAGE_MANAGERS['apt-get']
        self._yum = Helper.PACKAGE_MANAGERS['yum']
        self._find_executable = Helper.find_executable

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        # pylint: disable=protected-access
        Helper.confirm = self._confirm
        Helper._check_call = self._check_call
        Helper._check_output = self._check_output
        Helper.download_and_expand = self._download_and_expand
        Helper.PACKAGE_MANAGERS['port'] = self._port
        Helper.PACKAGE_MANAGERS['apt-get'] = self._apt_get
        Helper.PACKAGE_MANAGERS['yum'] = self._yum
        platform.system = self._system
        Helper.find_executable = self._find_executable
        super(HelperUT, self).tearDown()


class HelperGenericTest(HelperUT):
    """Test cases for generic Helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = Helper("generic")
        super(HelperGenericTest, self).setUp()

    def test_check_call_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist."""
        # pylint: disable=protected-access
        Helper._check_call = self._check_call
        self.assertRaises(HelperNotFoundError,
                          Helper._check_call, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          Helper._check_call,
                          ["not_a_command"], require_success=True)

    def test_check_call_helpererror(self):
        """HelperError if executable fails and require_success is set."""
        # pylint: disable=protected-access
        Helper._check_call = self._check_call
        with self.assertRaises(HelperError) as cm:
            Helper._check_call(["false"])
        self.assertEqual(cm.exception.errno, 1)

        Helper._check_call(["false"], require_success=False)

    @mock.patch('subprocess.check_call')
    def test_check_call_permissions_needed(self, mock_check_call):
        """Test cases where sudo permission is needed."""
        # pylint: disable=protected-access
        Helper._check_call = self._check_call

        def raise_oserror(args, **_):
            """Raise an OSError unless using 'sudo'."""
            if args[0] != 'sudo':
                raise OSError(13, 'permission denied')
            return
        mock_check_call.side_effect = raise_oserror

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

    def test_helper_not_found(self):
        """Make sure helper.path is None if find_executable fails."""
        Helper.find_executable = self.stub_find_executable
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

    def test_call_helper_no_install(self):
        """If not installed, and user declines, raise HelperNotFoundError."""
        self.default_confirm_response = False
        self.assertRaises(HelperNotFoundError,
                          self.helper.call_helper, ["Hello!"])

    def test_download_and_expand(self):
        """Validate the download_and_expand() context_manager."""
        # Remove our stub for this test only
        Helper.download_and_expand = self._download_and_expand
        try:
            with Helper.download_and_expand(
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
        except ConnectionError:
            # unable to connect to github - might be an isolated environment
            self.fail("ConnectionError when trying to download from GitHub")
        # Temporary directory should be cleaned up when done
        self.assertFalse(os.path.exists(directory))
