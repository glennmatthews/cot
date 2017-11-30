#!/usr/bin/env python
#
# ut.py - Test case wrapper for the Common OVF Tool suite
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Generic unit test case implementation for COT."""

from __future__ import print_function

from difflib import unified_diff
import os.path
import glob
import tempfile
import shutil
import re
import time
import logging
from logging.handlers import BufferingHandler
# Make sure there's always a "no-op" logging handler.
from logging import NullHandler

from pkg_resources import resource_filename

from COT.helpers import helpers, HelperError

try:
    import unittest2 as unittest
except ImportError:
    import unittest

logger = logging.getLogger(__name__)


logging.getLogger('COT').addHandler(NullHandler())


class UTLoggingHandler(BufferingHandler):
    """Captures log messages to a buffer so we can inspect them for testing."""

    def __init__(self, testcase):
        """Create a logging handler for the given test case.

        Args:
          testcase (unittest.TestCase): Owner of this logging handler.
        """
        BufferingHandler.__init__(self, capacity=0)
        self.setLevel(logging.DEBUG)
        self.testcase = testcase

    def emit(self, record):
        """Add the given log record to our internal buffer.

        Args:
          record (LogRecord): Record to store.
        """
        self.buffer.append(record.__dict__)

    def shouldFlush(self, record):  # noqa: N802
        """Return False - we only flush manually.

        Args:
          record (LogRecord): Record to ignore.
        Returns:
          bool: always False
        """
        return False

    def logs(self, **kwargs):
        """Look for log entries matching the given dict.

        Args:
          kwargs (dict): logging arguments to match against.
        Returns:
          list: List of record(s) that matched.
        """
        matches = []
        for record in self.buffer:
            found_match = True
            for (key, value) in kwargs.items():
                if key == 'msg':
                    # Regexp match
                    if not re.search(value, str(record.get(key))):
                        found_match = False
                        break
                elif key == 'args':
                    for (exp, act) in zip(value, record.get(key)):
                        if not re.search(str(exp), str(act)):
                            found_match = False
                            break
                elif not value == record.get(key):
                    found_match = False
                    break
            if found_match:
                matches.append(record)
        return matches

    def assertLogged(self, info='', **kwargs):  # noqa: N802
        """Fail unless the given log messages were each seen exactly once.

        Args:
          info (str): Optional string to prepend to any failure messages.
          kwargs (dict): logging arguments to match against.

        Raises:
          AssertionError: if an expected log message was not seen
          AssertionError: if an expected log message was seen more than once
        """
        matches = self.logs(**kwargs)
        if not matches:
            self.testcase.fail(
                info + "Expected logs matching {0} but none were logged!"
                .format(kwargs))
        if len(matches) > 1:
            self.testcase.fail(
                info + "Message {0} was logged {1} times instead of once!"
                .format(kwargs, len(matches)))
        for match in matches:
            self.buffer.remove(match)

    def assertNoLogsOver(self, max_level, info=''):  # noqa: N802
        """Fail if any logs are logged higher than the given level.

        Args:
          max_level (int): Highest logging level to permit.
          info (str): Optional string to prepend to any failure messages.
        Raises:
          AssertionError: if any messages higher than max_level were seen
        """
        for level in (logging.CRITICAL, logging.ERROR, logging.WARNING,
                      logging.INFO, logging.VERBOSE, logging.DEBUG):
            if level <= max_level:
                return
            matches = self.logs(levelno=level)
            if matches:
                self.testcase.fail(
                    "{info}Found {len} unexpected {lvl} message(s):\n\n{msgs}"
                    .format(info=info,
                            len=len(matches),
                            lvl=logging.getLevelName(level),
                            msgs="\n\n".join([r['msg'] % r['args']
                                              for r in matches])))


def _localfile(name):
    """Get the absolute path to a local resource file.

    Args:
      name (str): File name.
    Returns:
      str: Absolute file path.
    """
    return os.path.abspath(resource_filename(__name__, name))


class COTTestCase(unittest.TestCase):  # noqa: N801
    """Subclass of unittest.TestCase adding some additional behaviors.

    For the parameters, see :class:`unittest.TestCase`.
    """

    FILE_SIZE = {}
    for filename in [
            'blank.vmdk',
            'input.iso',
            'input.vmdk',
            'minimal.ovf',
            'sample_cfg.txt',
    ]:
        FILE_SIZE[filename] = os.path.getsize(_localfile(filename))

    # Standard ERROR logger messages we may expect at various points:
    # TODO: change these to functions so we can populate 'args' for each
    NONEXISTENT_FILE = {
        'levelname': 'ERROR',
        'msg': "File '%s' referenced in the OVF.*does not exist",
    }
    FILE_DISAPPEARED = {
        'levelname': 'ERROR',
        'msg': "Referenced file '%s' does not exist",
    }

    # Standard WARNING logger messages we may expect at various points:
    UNRECOGNIZED_PRODUCT_CLASS = {
        'levelname': 'NOTICE',
        'msg': "Unrecognized product class.*Treating .*as a generic platform",
    }
    ADDRESS_ON_PARENT_NOT_SPECIFIED = {
        'levelname': 'WARNING',
        'msg': "New disk address on parent not specified, guessing.*%s",
        'args': ('0', ),
    }
    REMOVING_FILE = {
        'levelname': 'NOTICE',
        'msg': "Removing reference to missing file",
    }
    DELETING_DISK = {
        'levelname': 'NOTICE',
        'msg': "Existing element will be deleted.",
    }
    DELETING_DISK_SECTION = {
        'levelname': 'NOTICE',
        'msg': "removing DiskSection",
    }

    # Set default OVF file. Individual test cases can use others
    input_ovf = _localfile("input.ovf")
    # Alternative OVF files:
    #
    # Absolute minimal OVF descriptor needed to satisfy ovftool.
    # Please verify any changes made to this file by running
    # "ovftool --schemaValidate minimal.ovf"
    minimal_ovf = _localfile("minimal.ovf")
    # IOSv OVF
    iosv_ovf = _localfile("iosv.ovf")
    # CSR1000V OVF - legacy
    csr_ovf = _localfile("csr1000v.ovf")
    # CSR1000V OVF as of 2017
    csr_ovf_2017 = _localfile("csr1000v_2017.ovf")
    # v0.9 OVF
    v09_ovf = _localfile("v0.9.ovf")
    # v2.0 OVF from VirtualBox
    v20_vbox_ovf = _localfile("ubuntu.2.0.ovf")
    # OVF with lots of custom VMware extensions
    vmware_ovf = _localfile("vmware.ovf")
    # OVF with various odd/invalid contents
    invalid_ovf = _localfile("invalid.ovf")
    # OVF claiming to be a "version 3" OVF format, which doesn't exist yet
    ersatz_v3_ovf = _localfile("ersatz_ovf_3.0.ovf")

    # Manifests corresponding to OVFs above
    input_manifest = _localfile("input.mf")
    v20_vbox_manifest = _localfile("ubuntu.2.0.mf")

    # Some canned disk images and other files too
    input_iso = _localfile("input.iso")
    input_vmdk = _localfile("input.vmdk")
    blank_vmdk = _localfile("blank.vmdk")
    sample_cfg = _localfile("sample_cfg.txt")

    @staticmethod
    def invalid_hardware_warning(profile, value, kind):
        """Warning log message for invalid hardware.

        Args:
          profile (str): Config profile, or "".
          value (object): Invalid value
          kind (str): Label for this hardware kind.
        Returns:
          dict: kwargs suitable for passing into :meth:`assertLogged`
        """
        msg = ""
        if profile:
            msg += "In profile '{0}':".format(profile)
        msg += "(Unsupported )?[vV]alue '{0}' for {1}".format(value, kind)
        return {
            'levelname': 'WARNING',
            'msg': msg,
        }

    def __init__(self, method_name='runTest'):
        """Add logging handler to generic UT initialization.

        For the parameters, see :class:`unittest.TestCase`.
        """
        super(COTTestCase, self).__init__(method_name)
        self.logging_handler = UTLoggingHandler(self)

    def check_diff(self, expected, file1=None, file2=None):
        """Get diff of two files and compare it to the expected output.

        If the files are unspecified, defaults to comparing the input OVF file
        and the temporary output OVF file.

        Args:
          expected (str): Expected diff output
          file1 (str): File path to compare (default: input.ovf file)
          file2 (str): File path to compare (default: output.ovf file)

        Raises:
          AssertionError: if the two files do not have identical contents.
        """
        if file1 is None:
            file1 = self.input_ovf
        if file2 is None:
            file2 = self.temp_file

        with open(file1) as fileobj1, open(file2) as fileobj2:
            diff = unified_diff(fileobj1.readlines(), fileobj2.readlines(),
                                fromfile=file1, tofile=file2,
                                n=1)   # number of context lines
        # Strip line numbers and file names from the diff
        # to keep the UT more maintainable
        clean_diff = ""
        for line in diff:
            if re.match("^[-+]{3}", line):
                # --- COT/tests/input.ovf Tue Sep 24 13:02:08 2013
                # +++ foo.ovf     Tue Sep 24 13:03:32 2013
                pass
            elif re.match("^@", line):
                # @@ -138,2 +145,10 @@
                if clean_diff != "":
                    clean_diff += "...\n"
            else:
                clean_diff += line
        # Strip leading/trailing whitespace for easier comparison:
        if clean_diff.strip() != expected.strip():
            self.fail("'diff {0} {1}' failed - expected:\n{2}\ngot:\n{3}"
                      .format(file1, file2, expected, clean_diff))

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        # keep log messages from interfering with our tests
        logging.getLogger('COT').setLevel(logging.DEBUG)
        self.logging_handler.setLevel(logging.NOTSET)
        self.logging_handler.flush()
        logging.getLogger('COT').addHandler(self.logging_handler)

        self.start_time = time.time()
        # Set a temporary directory for us to write our OVF to
        self.temp_dir = tempfile.mkdtemp(prefix="cot_ut")
        self.temp_file = os.path.join(self.temp_dir, "out.ovf")
        logger.debug("Created temp dir %s", self.temp_dir)
        # Monitor the global temp directory to make sure COT cleans up
        self.tmps = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cot*')))

        self.validate_output_with_ovftool = True

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        # Fail if any WARNING/ERROR/CRITICAL logs were generated
        self.logging_handler.assertNoLogsOver(logging.INFO)

        logging.getLogger('COT').removeHandler(self.logging_handler)

        self.validate_with_ovftool(self.temp_file)

        # Delete the temporary directory
        if os.path.exists(self.temp_dir):
            logger.debug("Deleting temp dir %s", self.temp_dir)
            shutil.rmtree(self.temp_dir)
        self.temp_dir = None
        self.temp_file = None

        tmps2 = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cot*')))
        delta = tmps2 - self.tmps
        if delta:
            self.fail("Temp directory(s) {0} left over after test!"
                      .format(delta))

        # Clear output caches for helper commands:
        for helper in helpers.values():
            helper.cached_output.clear()

        # Let's try to keep things lean...
        delta_t = time.time() - self.start_time
        if delta_t > 5.0:
            print("\nWARNING: Test {0} took {1:.3f} seconds to execute. "
                  "Consider refactoring it to be more efficient."
                  .format(self.id(), delta_t))

    def validate_with_ovftool(self, filename=None):
        """Use OVFtool to validate the given OVF/OVA file.

        Args:
          filename (str): File name to validate (optional, default is
              :attr:`temp_file`).
        """
        if filename is None:
            filename = self.temp_file
        if (self.validate_output_with_ovftool and
                os.path.exists(filename) and
                helpers['ovftool']):
            try:
                helpers['ovftool'].call(['--schemaValidate', filename])
            except HelperError as exc:
                self.fail("OVF not valid according to ovftool:\n{0}"
                          .format(exc.strerror))

    def assertLogged(self, info='', **kwargs):  # noqa: N802
        """Fail unless the given logs were generated.

        For the parameters, see :meth:`UTLoggingHandler.assertLogged`.
        """
        self.logging_handler.assertLogged(info=info, **kwargs)

    def assertNoLogsOver(self, max_level, info=''):  # noqa: N802
        """Fail if any logs were logged higher than the given level.

        For the parameters, see :meth:`UTLoggingHandler.assertNoLogsOver`.
        """
        self.logging_handler.assertNoLogsOver(max_level, info=info)
