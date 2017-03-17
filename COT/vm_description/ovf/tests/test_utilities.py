#!/usr/bin/env python
#
# test_utilities.py - Unit test cases for COT OVF/OVA utility functions
#
# February 2017, Glenn F. Matthews
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

"""Unit test cases for COT.vm_description.ovf.utilities module.

Most test cases are implemented as doctests in the module itself;
this is for additional tests that are impractical as doctests.
"""

from COT.tests import COTTestCase
from COT.vm_description.ovf.utilities import programmatic_bytes_to_int


class TestProgrammaticUnits(COTTestCase):
    """Test cases for programmatic unit conversion functions."""

    def test_programmatic_bytes_to_int(self):
        """Test programmatic_bytes_to_int() function."""
        # unknown units are ignored with a warning
        self.assertEqual(programmatic_bytes_to_int("100", "foobar"), 100)
        self.assertLogged(levelname='WARNING',
                          msg="Unknown programmatic units string '%s'",
                          args=('foobar',))
