#!/usr/bin/env python
#
# November 2016, Glenn F. Matthews
# Copyright (c) 2016-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for COT.vm_description.ovf.OVFHardware class."""

from COT.tests import COTTestCase
from COT.vm_description.ovf import OVF


class TestOVFHardware(COTTestCase):
    """Unit test cases for the OVFHardware class."""

    def test_basic_sanity(self):
        """Make sure basic loading is successful and APIs work."""
        with OVF(self.input_ovf, None) as ovf:
            hardware = ovf.hardware
            self.assertEqual(ovf, hardware.ovf)
            self.assertEqual(13, len(hardware.item_dict))
            self.assertEqual('14', hardware.find_unused_instance_id())
            self.assertEqual(2, len(hardware.find_all_items('ide')))
            self.assertEqual(1, len(hardware.find_all_items(
                'ide', properties={ovf.ADDRESS: '1'})))
            self.assertEqual(0, len(hardware.find_all_items(
                'ide', properties={ovf.ADDRESS: '2'})))
            self.assertNotEqual(None, hardware.find_item('harddisk'))
            self.assertEqual(None, hardware.find_item('usb'))
            self.assertRaises(LookupError, hardware.find_item, 'ide')
            self.assertEqual(1, hardware.get_item_count('ethernet', None))
            self.assertEqual(3, hardware.get_item_count(
                'ethernet', "4CPU-4GB-3NIC"))
            self.assertEqual(3, hardware.get_item_count_per_profile(
                'ethernet', None)["4CPU-4GB-3NIC"])

    def test_find_item_multiple_matches(self):
        """Check find_item raises LookupError if multiple matches are found."""
        with OVF(self.input_ovf, None) as ovf:
            self.assertRaisesRegex(
                LookupError,
                r"multiple matching 'ide' Items",
                ovf.hardware.find_item, resource_type='ide')

    def test_find_item_no_matches(self):
        """Test that find_item returns None if no matches are found."""
        with OVF(self.input_ovf, None) as ovf:
            self.assertEqual(None, ovf.hardware.find_item(resource_type='usb'))
