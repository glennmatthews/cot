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
import sys
import platform
import time
import logging
from logging.handlers import BufferingHandler
# Make sure there's always a "no-op" logging handler.
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        """No-op logging handler."""

        def emit(self, record):
            """Do nothing.

            Args:
              record (LogRecord): Record to ignore.
            """
            pass

import traceback
try:
    import StringIO
except ImportError:
    import io as StringIO

from pkg_resources import resource_filename
import mock

from COT.helpers import helpers, HelperError

try:
    import unittest2 as unittest
except ImportError:
    import unittest
from verboselogs import VerboseLogger
logging.setLoggerClass(VerboseLogger)

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
        for r in matches:
            self.buffer.remove(r)

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
                    "{info}Found {len} unexpected {lvl} message(s):\n{msgs}"
                    .format(info=info,
                            len=len(matches),
                            lvl=logging.getLevelName(level),
                            msgs="\n".join(["msg: {0}, args: {1}"
                                            .format(r['msg'], r['args'])
                                            for r in matches])))


class COT_UT(unittest.TestCase):  # noqa: N801
    """Subclass of unittest.TestCase adding some additional behaviors.

    For the parameters, see :class:`unittest.TestCase`.
    """

    FILE_SIZE = {}
    for filename in [
            'input.iso',
            'input.vmdk',
            'blank.vmdk',
            'sample_cfg.txt',
    ]:
        FILE_SIZE[filename] = os.path.getsize(resource_filename(__name__,
                                                                filename))

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
    TYPE_NOT_SPECIFIED_GUESS_HARDDISK = {
        'levelname': 'WARNING',
        'msg': "drive type not specified.*guessing.*based on file extension",
        'args': ('harddisk', ),
    }
    TYPE_NOT_SPECIFIED_GUESS_CDROM = {
        'levelname': 'WARNING',
        'msg': "drive type not specified.*guessing.*based on file extension",
        'args': ('cdrom', ),
    }
    CONTROLLER_NOT_SPECIFIED_GUESS_IDE = {
        'levelname': 'WARNING',
        'msg': "Guessing controller type.*based on disk drive type",
        'args': ('ide', r'.*', r'.*'),
    }
    UNRECOGNIZED_PRODUCT_CLASS = {
        'levelname': 'WARNING',
        'msg': "Unrecognized product class.*Treating as a generic platform",
    }
    ADDRESS_ON_PARENT_NOT_SPECIFIED = {
        'levelname': 'WARNING',
        'msg': "New disk address on parent not specified, guessing.*%s",
        'args': ('0', ),
    }
    REMOVING_FILE = {
        'levelname': 'WARNING',
        'msg': "Removing reference to missing file",
    }
    OVERWRITING_FILE = {
        'levelname': 'WARNING',
        'msg': "Overwriting existing File in OVF",
    }
    OVERWRITING_DISK = {
        'levelname': 'WARNING',
        'msg': "Overwriting existing Disk in OVF",
    }
    DELETING_DISK = {
        'levelname': 'WARNING',
        'msg': "Existing element will be deleted.",
    }
    DELETING_DISK_SECTION = {
        'levelname': 'WARNING',
        'msg': "removing DiskSection",
    }
    OVERWRITING_DISK_ITEM = {
        'levelname': 'WARNING',
        'msg': "Overwriting existing disk Item in OVF",
    }

    @staticmethod
    def localfile(name):
        """Get the absolute path to a local resource file.

        Args:
          name (str): File name.
        Returns:
          str: Absolute file path.
        """
        return os.path.abspath(resource_filename(__name__, name))

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
        super(COT_UT, self).__init__(method_name)
        self.logging_handler = UTLoggingHandler(self)
        self.instance = None

    def set_vm_platform(self, plat_class):
        """Force the VM under test to use a particular Platform class.

        Args:
           plat_class (COT.platforms.Platform): Platform class to use
        """
        # pylint: disable=protected-access
        self.instance.vm._platform = plat_class()

    def check_cot_output(self, expected):
        """Grab the output from COT and check it against expected output.

        Args:
          expected (str): Expected output
        Raises:
          AssertionError: if an error is raised by COT when run
          AssertionError: if the output returned does not match expected.
        """
        with mock.patch('sys.stdout', new_callable=StringIO.StringIO) as so:
            try:
                self.instance.run()
            except (TypeError, ValueError, SyntaxError, LookupError):
                self.fail(traceback.format_exc())
            output = so.getvalue()
        self.maxDiff = None
        self.assertMultiLineEqual(expected.strip(), output.strip())

    def check_diff(self, expected, file1=None, file2=None):
        """Get diff of two files and compare it to the expected output.

        If the files are unspecified, defaults to comparing the input OVF file
        and the temporary output OVF file.

        Note that comparison of OVF files is currently skipped when
        running under Python 2.6, as it produces different XML output than
        later Python versions.

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

        if re.search("ovf", file1) and sys.hexversion < 0x02070000:
            logger.info("OVF file diff comparison skipped "
                        "due to old Python version (%s)",
                        platform.python_version())
            return

        with open(file1) as f1:
            with open(file2) as f2:
                diff = unified_diff(f1.readlines(), f2.readlines(),
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
        # Set default OVF file. Individual test cases can use others
        self.input_ovf = self.localfile("input.ovf")
        # Alternative OVF files:
        #
        # Absolute minimal OVF descriptor needed to satisfy ovftool.
        # Please verify any changes made to this file by running
        # "ovftool --schemaValidate minimal.ovf"
        self.minimal_ovf = self.localfile("minimal.ovf")
        # IOSv OVF
        self.iosv_ovf = self.localfile("iosv.ovf")
        # CSR1000V OVF
        self.csr_ovf = self.localfile("csr1000v.ovf")
        # v0.9 OVF
        self.v09_ovf = self.localfile("v0.9.ovf")
        # v2.0 OVF from VirtualBox
        self.v20_vbox_ovf = self.localfile("ubuntu.2.0.ovf")
        # OVF with lots of custom VMware extensions
        self.vmware_ovf = self.localfile("vmware.ovf")
        # OVF with various odd/invalid contents
        self.invalid_ovf = self.localfile("invalid.ovf")

        # Some canned disk images and other files too
        self.input_iso = os.path.abspath(self.localfile("input.iso"))
        self.input_vmdk = self.localfile("input.vmdk")
        self.blank_vmdk = self.localfile("blank.vmdk")
        self.sample_cfg = self.localfile("sample_cfg.txt")

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

        if self.instance:
            self.instance.destroy()
            self.instance = None

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
            except HelperError as e:
                self.fail("OVF not valid according to ovftool:\n{0}"
                          .format(e.strerror))

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
