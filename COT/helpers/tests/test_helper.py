#!/usr/bin/env python
#
# test_helpers.py - Unit test cases for COT.helpers submodule.
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2014-2015 the COT project developers.
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
from requests.exceptions import ConnectionError

from COT.tests.ut import COT_UT
import COT.helpers.helper
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

    def stub_check_call(self, argv, require_success=True, **kwargs):
        """Stub for Helper._check_call - store the argv and do nothing."""
        logger.info("stub_check_call({0}, {1})"
                    .format(argv, require_success))
        self.last_argv.append(argv)

    def stub_check_output(self, argv, require_success=True, **kwargs):
        """Stub for Helper._check_output - return canned output."""
        logger.info("stub_check_output({0}, {1})"
                    .format(argv, require_success))
        self.last_argv.append(argv)
        if self.fake_output is not None:
            return self.fake_output
        return self._check_output(argv, require_success)

    def stub_find_executable(self, name):
        """Stub for Helper.find_executable - returns a fixed response."""
        logger.info("stub_find_executable({0})".format(name))
        return self.fake_path

    @contextlib.contextmanager
    def stub_download_and_expand(self, url):
        """Stub for Helper.download_and_expand - create a fake directory."""
        from COT.helpers.helper import TemporaryDirectory
        with TemporaryDirectory(prefix=("cot_ut_" + self.helper.name)) as d:
            yield d

    def stub_confirm(self, prompt, force=False):
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
        self._check_call = Helper._check_call
        Helper._check_call = self.stub_check_call
        self._check_output = Helper._check_output
        Helper._check_output = self.stub_check_output
        self._download_and_expand = Helper.download_and_expand
        Helper.download_and_expand = self.stub_download_and_expand
        self.default_confirm_response = True
        self._confirm = COT.helpers.helper.confirm
        COT.helpers.helper.confirm = self.stub_confirm
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
        COT.helpers.helper.confirm = self._confirm
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
        Helper._check_call = self._check_call
        self.assertRaises(HelperNotFoundError,
                          Helper._check_call, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          Helper._check_call,
                          ["not_a_command"], require_success=True)

    def test_check_call_helpererror(self):
        """HelperError if executable fails and require_success is set."""
        Helper._check_call = self._check_call
        with self.assertRaises(HelperError) as cm:
            Helper._check_call(["false"])
        self.assertEqual(cm.exception.errno, 1)

        Helper._check_call(["false"], require_success=False)

    def test_check_output_helpernotfounderror(self):
        """HelperNotFoundError if executable doesn't exist."""
        self.assertRaises(HelperNotFoundError,
                          Helper._check_output, ["not_a_command"])
        self.assertRaises(HelperNotFoundError,
                          Helper._check_output, ["not_a_command"],
                          require_success=True)

    def test_check_output_helpererror(self):
        """HelperError if executable fails and require_success is set."""
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
        self.helper._path = True
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
