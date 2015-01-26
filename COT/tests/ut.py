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
from verboselogs import VerboseLogger

logging.setLoggerClass(VerboseLogger)

from COT.helper_tools import validate_ovf_for_esxi
from COT.helper_tools import HelperError, HelperNotFoundError

logger = logging.getLogger(__name__)


class COT_UT(unittest.TestCase):
    """Subclass of unittest.TestCase adding some additional behaviors we want
    for all of our test cases"""

    OVFTOOL_PRESENT = True

    FILE_SIZE = {}
    for filename in ['input.iso', 'input.vmdk', 'blank.vmdk']:
        FILE_SIZE[filename] = os.path.getsize(os.path.join(
            os.path.dirname(__file__), filename))

    def check_diff(self, expected, file1=None, file2=None):
        """Calls diff on the two files and compares it to the expected output.
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
        """Test case setup function called automatically prior to each test"""
        # keep log messages from interfering with our tests
        logging.getLogger('COT').setLevel(logging.CRITICAL)

        self.start_time = time.time()
        # Set default OVF file. Individual test cases can use others
        self.input_ovf = os.path.join(os.path.dirname(__file__), "input.ovf")
        # Alternative OVF files:
        #
        # Absolute minimal OVF descriptor needed to satisfy ovftool.
        # Please verify any changes made to this file by running
        # "ovftool --schemaValidate minimal.ovf"
        self.minimal_ovf = os.path.join(os.path.dirname(__file__),
                                        "minimal.ovf")
        # IOSv OVF
        self.iosv_ovf = os.path.join(os.path.dirname(__file__), "iosv.ovf")
        # v0.9 OVF
        self.v09_ovf = os.path.join(os.path.dirname(__file__), "v0.9.ovf")
        # v2.0 OVF from VirtualBox
        self.v20_vbox_ovf = os.path.join(os.path.dirname(__file__),
                                         "ubuntu.2.0.ovf")
        # OVF with lots of custom VMware extensions
        self.vmware_ovf = os.path.join(os.path.dirname(__file__), "vmware.ovf")
        # Set a temporary directory for us to write our OVF to
        self.temp_dir = tempfile.mkdtemp(prefix="cot_ut")
        self.temp_file = os.path.join(self.temp_dir, "out.ovf")
        logger.debug("Created temp dir {0}".format(self.temp_dir))
        # Monitor the global temp directory to make sure COT cleans up
        self.tmps = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cot*')))

        self.validate_output_with_ovftool = True

    def tearDown(self):
        """Test case cleanup function called automatically after each test"""

        if hasattr(self, 'instance'):
            self.instance.destroy()
            self.instance = None

        if (COT_UT.OVFTOOL_PRESENT and self.validate_output_with_ovftool
                and os.path.exists(self.temp_file)):
            # Ask OVFtool to validate that the output file is sane
            try:
                validate_ovf_for_esxi(self.temp_file)
            except HelperNotFoundError:
                print("\nWARNING: Unable to locate ovftool. "
                      "Some tests will be less thorough.")
                # Don't bother trying in future test cases
                COT_UT.OVFTOOL_PRESENT = False
            except HelperError as e:
                self.fail("OVF not valid according to ovftool:\n{0}"
                          .format(e.strerror))

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
