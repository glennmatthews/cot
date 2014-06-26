#!/usr/bin/env python
#
# ut.py - Test case wrapper for the Common OVF Tool suite
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

import unittest
import subprocess
from difflib import unified_diff
from os import devnull
import os.path
import tempfile
import shutil
import re
import time

from COT.helper_tools import *

class COT_UT(unittest.TestCase):
    """Subclass of unittest.TestCase adding some additional behaviors we want
    for all of our test cases"""

    OVFTOOL_PRESENT = True

    def check_diff(self, expected, file1=None, file2=None):
        """Calls diff on the two files and compares it to the expected output.
        If the files are unspecified, defaults to comparing the input OVF file
        and the temporary output OVF file.
        """
        if file1 is None:
            file1 = self.input_ovf
        if file2 is None:
            file2 = self.temp_file
        diff = unified_diff(open(file1).readlines(), open(file2).readlines(),
                            fromfile=file1, tofile=file2,
                            n=1) # number of context lines
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


    def call_no_output(self, argv, result=0):
        """Like subprocess.call, but suppress stdout and stderr by default"""
        p = subprocess.Popen(argv, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        self.assertEqual(result, p.returncode,
                         "expected return code {0} when calling '{1}'\n"
                         "but got {2}:\n{3}\n{4}"
                         .format(result,
                                 " ".join(argv),
                                 p.returncode,
                                 stdout.decode(),
                                 stderr.decode()))
        return p.returncode


    def call_cot(self, argv, result=0):
        """Invoke cot with the specified arguments, suppressing stdout and
        stderr, and return its return code"""
        argv.insert(0, os.path.join(os.path.dirname(__file__),
                                    "..", "..", "bin", "cot"))
        import glob
        tmps = set(glob.glob(os.path.join("/tmp", "cot*")))
        rc = self.call_no_output(argv, result)
        tmps2 = set(glob.glob(os.path.join("/tmp", "cot*")))
        delta = tmps2 - tmps
        if delta:
            self.fail("Temp directory(s) {0} left over after calling '{1}'!"
                      .format(delta, " ".join(argv)))
        return rc


    def setUp(self):
        """Test case setup function called automatically prior to each test"""
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
        # OVF with lots of custom VMware extensions
        self.vmware_ovf = os.path.join(os.path.dirname(__file__), "vmware.ovf")
        # Set a temporary directory for us to write our OVF to
        self.temp_dir = tempfile.mkdtemp(prefix="cot_ut")
        self.temp_file = os.path.join(self.temp_dir, "out.ovf")


    def tearDown(self):
        """Test case cleanup function called automatically after each test"""

        if COT_UT.OVFTOOL_PRESENT and os.path.exists(self.temp_file):
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
            shutil.rmtree(self.temp_dir)
        self.temp_dir = None
        self.temp_file = None

        # Let's try to keep things lean...
        delta_t = time.time() - self.start_time
        if delta_t > 5.0:
            print("\nWARNING: Test {0} took {1:.3f} seconds to execute. "
                  "Consider refactoring it to be more efficient."
                  .format(self.id(), delta_t))
