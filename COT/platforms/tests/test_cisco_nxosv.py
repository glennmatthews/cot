# test_cisco_nxosv.py - Unit test cases for Cisco NXOSv platform
#
# October 2016, Glenn F. Matthews
# Copyright (c) 2014-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for NXOSv platform."""

import unittest
from COT.platforms.cisco_nxosv import NXOSv
from COT.data_validation import (
    ValueUnsupportedError, ValueTooLowError, ValueTooHighError
)


class TestNXOSv(unittest.TestCase):
    """Test cases for Cisco NX-OSv platform handling."""

    cls = NXOSv

    def test_nic_name(self):
        """Test NIC name construction."""
        self.assertEqual(self.cls.guess_nic_name(1),
                         "mgmt0")
        self.assertEqual(self.cls.guess_nic_name(2),
                         "Ethernet2/1")
        self.assertEqual(self.cls.guess_nic_name(3),
                         "Ethernet2/2")
        self.assertEqual(self.cls.guess_nic_name(4),
                         "Ethernet2/3")
        # ...
        self.assertEqual(self.cls.guess_nic_name(49),
                         "Ethernet2/48")
        self.assertEqual(self.cls.guess_nic_name(50),
                         "Ethernet3/1")

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_cpu_count, 0)
        self.cls.validate_cpu_count(1)
        self.cls.validate_cpu_count(8)
        self.assertRaises(ValueTooHighError, self.cls.validate_cpu_count, 9)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError,
                          self.cls.validate_memory_amount, 2047)
        self.cls.validate_memory_amount(2048)
        self.cls.validate_memory_amount(8192)
        self.assertRaises(ValueTooHighError,
                          self.cls.validate_memory_amount, 8193)

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_nic_count, -1)
        self.cls.validate_nic_count(0)
        self.cls.validate_nic_count(32)
        # No upper bound known at present

    def test_nic_type(self):
        """Test NIC valid and invalid types."""
        self.assertRaises(ValueUnsupportedError,
                          self.cls.validate_nic_type, "E1000e")
        self.cls.validate_nic_type("E1000")
        self.assertRaises(ValueUnsupportedError,
                          self.cls.validate_nic_type, "PCNet32")
        self.cls.validate_nic_type("virtio")
        self.assertRaises(ValueUnsupportedError,
                          self.cls.validate_nic_type, "VMXNET3")

    def test_serial_count(self):
        """Test serial port range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_serial_count, 0)
        self.cls.validate_serial_count(1)
        self.cls.validate_serial_count(2)
        self.assertRaises(ValueTooHighError, self.cls.validate_serial_count, 3)
