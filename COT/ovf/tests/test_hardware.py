#!/usr/bin/env python
#
# November 2016, Glenn F. Matthews
# Copyright (c) 2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for COT.ovf.OVFHardware class."""

from COT.tests.ut import COT_UT

from COT.vm_context_manager import VMContextManager


class TestOVFHardware(COT_UT):
    """Unit test cases for the OVFHardware class."""

    def test_find_item_multiple_matches(self):
        """Check find_item raises LookupError if multiple matches are found."""
        with VMContextManager(self.input_ovf) as ovf:
            hw = ovf.hardware
            self.assertRaisesRegex(
                LookupError,
                r"multiple matching 'ide' Items",
                hw.find_item, resource_type='ide')

    def test_find_item_no_matches(self):
        """Test that find_item returns None if no matches are found."""
        with VMContextManager(self.input_ovf) as ovf:
            hw = ovf.hardware
            self.assertEqual(None, hw.find_item(resource_type='usb'))
