#!/usr/bin/env python
#
# ut.py - Test case wrapper for the Common OVF Tool suite
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2015 the COT project developers.
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

try:
    import unittest2 as unittest
except ImportError:
    import unittest
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
from pkg_resources import resource_filename
import traceback
try:
    import StringIO
except ImportError:
    import io as StringIO

from verboselogs import VerboseLogger
logging.setLoggerClass(VerboseLogger)

logger = logging.getLogger(__name__)

# Make sure there's always a "no-op" logging handler.
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        """No-op logging handler."""

        def emit(self, record):
            """Do nothing."""
            pass

logging.getLogger('COT').addHandler(NullHandler())


class UTLoggingHandler(BufferingHandler):
    """Captures log messages to a buffer so we can inspect them for testing."""

    def __init__(self, testcase):
        """Create a logging handler for the given test case."""
        BufferingHandler.__init__(self, capacity=0)
        self.setLevel(logging.DEBUG)
        self.testcase = testcase

    def emit(self, record):
        """Add the given log record to our internal buffer."""
        self.buffer.append(record.__dict__)

    def shouldFlush(self, record):
        """Return False - we only flush manually."""
        return False

    def logs(self, **kwargs):
        """Look for log entries matching the given dict."""
        matches = []
        for record in self.buffer:
            found_match = True
            for (key, value) in kwargs.items():
                if key == 'msg':
                    # Regexp match
                    if not re.search(value, str(record.get(key))):
                        found_match = False
                        break
                elif not value == record.get(key):
                    found_match = False
                    break
            if found_match:
                matches.append(record)
        return matches

    def assertLogged(self, **kwargs):
        """Fail unless the given log messages were each seen exactly once."""
        matches = self.logs(**kwargs)
        if not matches:
            self.testcase.fail(
                "Expected logs matching {0} but none were logged!"
                .format(kwargs))
        if len(matches) > 1:
            self.testcase.fail(
                "Message {0} was logged {1} times instead of once!"
                .format(kwargs, len(matches)))
        for r in matches:
            self.buffer.remove(r)

    def assertNoLogsOver(self, max_level):
        """Fail if any logs are logged higher than the given level."""
        for level in (logging.CRITICAL, logging.ERROR, logging.WARNING,
                      logging.INFO, logging.VERBOSE, logging.DEBUG):
            if level <= max_level:
                return
            matches = self.logs(levelno=level)
            if matches:
                self.testcase.fail(
                    "Found {length} unexpected {level} message(s):\n{messages}"
                    .format(length=len(matches),
                            level=logging.getLevelName(level),
                            messages="\n".join([str(r['msg']) for
                                                r in matches])))


class COT_UT(unittest.TestCase):
    """Subclass of unittest.TestCase adding some additional behaviors."""

    from COT.helpers.ovftool import OVFTool

    OVFTOOL = OVFTool()

    FILE_SIZE = {}
    for filename in ['input.iso', 'input.vmdk', 'blank.vmdk']:
        FILE_SIZE[filename] = os.path.getsize(resource_filename(__name__,
                                                                filename))

    # Standard ERROR logger messages we may expect at various points:
    NONEXISTENT_FILE = {
        'levelname': 'ERROR',
        'msg': "File '.*' referenced in the OVF.*does not exist",
    }
    FILE_DISAPPEARED = {
        'levelname': 'ERROR',
        'msg': "Referenced file '.*' does not exist",
    }

    # Standard WARNING logger messages we may expect at various points:
    TYPE_NOT_SPECIFIED_GUESS_HARDDISK = {
        'levelname': 'WARNING',
        'msg': "disk type not specified.*guessing.*harddisk.*extension",
    }
    TYPE_NOT_SPECIFIED_GUESS_CDROM = {
        'levelname': 'WARNING',
        'msg': "disk type not specified.*guessing.*cdrom.*extension",
    }
    CONTROLLER_NOT_SPECIFIED_GUESS_IDE = {
        'levelname': 'WARNING',
        'msg': "Guessing controller type.*ide.*based on disk type",
    }
    UNRECOGNIZED_PRODUCT_CLASS = {
        'levelname': 'WARNING',
        'msg': "Unrecognized product class.*Treating as a generic product",
    }
    ADDRESS_ON_PARENT_NOT_SPECIFIED = {
        'levelname': 'WARNING',
        'msg': "New disk address on parent not specified, guessing.*0",
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

    def __init__(self, method_name='runTest'):
        """Add logging handler to generic UT initialization."""
        super(COT_UT, self).__init__(method_name)
        self.logging_handler = UTLoggingHandler(self)

    def check_cot_output(self, expected):
        """Grab the output from COT and check it against expected output."""
        sys.stdout = StringIO.StringIO()
        output = None
        try:
            self.instance.run()
        except (TypeError, ValueError, SyntaxError, LookupError):
            self.fail(traceback.format_exc())
        finally:
            output = sys.stdout.getvalue()
            sys.stdout = sys.__stdout__
        self.maxDiff = None
        self.assertMultiLineEqual(expected.strip(), output.strip())

    def check_diff(self, expected, file1=None, file2=None):
        """Get diff of two files and compare it to the expected output.

        If the files are unspecified, defaults to comparing the input OVF file
        and the temporary output OVF file.

        Note that comparison of OVF files is currently skipped when
        running under Python 2.6, as it produces different XML output than
        later Python versions.
        """
        if file1 is None:
            file1 = self.input_ovf
        if file2 is None:
            file2 = self.temp_file

        if re.search("ovf", file1) and sys.hexversion < 0x02070000:
            print("OVF file diff comparison skipped "
                  "due to old Python version ({0})"
                  .format(platform.python_version()))
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
        self.input_ovf = resource_filename(__name__, "input.ovf")
        # Alternative OVF files:
        #
        # Absolute minimal OVF descriptor needed to satisfy ovftool.
        # Please verify any changes made to this file by running
        # "ovftool --schemaValidate minimal.ovf"
        self.minimal_ovf = resource_filename(__name__, "minimal.ovf")
        # IOSv OVF
        self.iosv_ovf = resource_filename(__name__, "iosv.ovf")
        # v0.9 OVF
        self.v09_ovf = resource_filename(__name__, "v0.9.ovf")
        # v2.0 OVF from VirtualBox
        self.v20_vbox_ovf = resource_filename(__name__, "ubuntu.2.0.ovf")
        # OVF with lots of custom VMware extensions
        self.vmware_ovf = resource_filename(__name__, "vmware.ovf")
        # OVF with various odd/invalid contents
        self.invalid_ovf = resource_filename(__name__, "invalid.ovf")

        # Some canned disk images too
        self.input_iso = resource_filename(__name__, "input.iso")
        self.input_vmdk = resource_filename(__name__, "input.vmdk")
        self.blank_vmdk = resource_filename(__name__, "blank.vmdk")

        # Set a temporary directory for us to write our OVF to
        self.temp_dir = tempfile.mkdtemp(prefix="cot_ut")
        self.temp_file = os.path.join(self.temp_dir, "out.ovf")
        logger.debug("Created temp dir {0}".format(self.temp_dir))
        # Monitor the global temp directory to make sure COT cleans up
        self.tmps = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cot*')))

        self.validate_output_with_ovftool = True

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        # Fail if any WARNING/ERROR/CRITICAL logs were generated
        self.logging_handler.assertNoLogsOver(logging.INFO)

        logging.getLogger('COT').removeHandler(self.logging_handler)

        if hasattr(self, 'instance'):
            self.instance.destroy()
            self.instance = None

        self.validate_with_ovftool(self.temp_file)

        # Delete the temporary directory
        if os.path.exists(self.temp_dir):
            logger.debug("Deleting temp dir {0}".format(self.temp_dir))
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
        """Use OVFtool to validate the given OVF/OVA file."""
        if filename is None:
            filename = self.temp_file
        if (self.OVFTOOL.path and self.validate_output_with_ovftool and
                os.path.exists(filename)):
            # Ask OVFtool to validate that the output file is sane
            from COT.helpers import HelperError
            try:
                self.OVFTOOL.validate_ovf(filename)
            except HelperError as e:
                self.fail("OVF not valid according to ovftool:\n{0}"
                          .format(e.strerror))

    def assertLogged(self, **kwargs):
        """Fail unless the given logs were generated.

        See :meth:`UTLoggingHandler.assertLogged`.
        """
        self.logging_handler.assertLogged(**kwargs)

    def assertNoLogsOver(self, max_level):
        """Fail if any logs were logged higher than the given level."""
        self.logging_handler.assertNoLogsOver(max_level)
