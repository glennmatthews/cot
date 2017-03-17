# September 2016, Glenn F. Matthews
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

"""Unit test cases for the COT.platforms package and its submodules."""

from COT.tests import COTTestCase
from COT.data_validation import ValueTooLowError
from COT.platforms import Platform


class PlatformTests(object):
    """Wrapper to "hide" the below abstract class from unittest module."""

    class PlatformTest(COTTestCase):
        """Abstract base class for testing of Platform subclasses."""

        cls = None
        """The Platform class or subclass being tested by this class."""
        product_string = ""
        """The product string for use with Platform.for_product_class()."""

        def setUp(self):
            """Test case setup method."""
            super(PlatformTests.PlatformTest, self).setUp()
            self.assertNotEqual(self.cls, None)
            self.ins = self.cls()    # pylint:disable=not-callable

        def test_controller_type_for_device(self):
            """Test platform-specific logic for device controllers."""
            self.assertEqual(self.ins.controller_type_for_device('harddisk'),
                             'ide')
            self.assertEqual(self.ins.controller_type_for_device('cdrom'),
                             'ide')

        def test_nic_name(self):
            """Test NIC name construction."""
            self.assertEqual(self.ins.guess_nic_name(1), "Ethernet1")
            self.assertEqual(self.ins.guess_nic_name(100), "Ethernet100")

        def test_cpu_count(self):
            """Test CPU count limits."""
            self.assertRaises(ValueTooLowError, self.ins.validate_cpu_count, 0)
            self.ins.validate_cpu_count(1)

        def test_memory_amount(self):
            """Test RAM allocation limits."""
            self.assertRaises(ValueTooLowError,
                              self.ins.validate_memory_amount, 0)
            self.ins.validate_memory_amount(1)

        def test_nic_count(self):
            """Test NIC range limits."""
            self.assertRaises(ValueTooLowError,
                              self.ins.validate_nic_count, -1)
            self.ins.validate_nic_count(0)

        def test_serial_count(self):
            """Test serial port range limits."""
            self.assertRaises(ValueTooLowError,
                              self.ins.validate_serial_count, -1)
            self.ins.validate_serial_count(0)

        def test_for_product_string(self):
            """Test Platform.for_product_string lookup of this class."""
            self.assertEqual(
                Platform.for_product_string(self.product_string).__class__,
                self.cls)
