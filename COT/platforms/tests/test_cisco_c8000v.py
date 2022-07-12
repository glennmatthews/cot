# test_cisco_c8000v.py - Unit test cases for Cisco C8000V platform
#
# October 2016, Glenn F. Matthews
# Copyright (c) 2014-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for C8000V platform."""

from COT.platforms.cisco_c8000v import C8000V
from COT.data_validation import (
    ValueUnsupportedError, ValueTooLowError, ValueTooHighError
)
from COT.platforms.tests import PlatformTests


class TestC8000V(PlatformTests.PlatformTest):
    """Test cases for Cisco C8000V platform handling."""

    cls = C8000V
    product_string = "com.cisco.c8000v"

    def test_controller_type_for_device(self):
        """Test platform-specific logic for device controllers."""
        self.assertEqual(self.ins.controller_type_for_device('harddisk'),
                         'scsi')
        self.assertEqual(self.ins.controller_type_for_device('cdrom'),
                         'ide')
        # fallthrough to parent class
        self.assertEqual(self.ins.controller_type_for_device('dvd'),
                         'ide')

    def test_nic_name(self):
        """Test NIC name construction."""
        self.assertEqual(self.ins.guess_nic_name(1),
                         "GigabitEthernet1")
        self.assertEqual(self.ins.guess_nic_name(2),
                         "GigabitEthernet2")
        self.assertEqual(self.ins.guess_nic_name(3),
                         "GigabitEthernet3")
        self.assertEqual(self.ins.guess_nic_name(4),
                         "GigabitEthernet4")

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_cpu_count, 0)
        self.ins.validate_cpu_count(1)
        self.ins.validate_cpu_count(2)
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_cpu_count, 3)
        self.ins.validate_cpu_count(4)
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_cpu_count, 5)
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_cpu_count, 6)
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_cpu_count, 7)
        self.ins.validate_cpu_count(8)
        self.assertRaises(ValueTooHighError, self.ins.validate_cpu_count, 9)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError,
                          self.ins.validate_memory_amount, 2559)
        self.ins.validate_memory_amount(2560)
        self.ins.validate_memory_amount(8192)
        self.assertRaises(ValueTooHighError,
                          self.ins.validate_memory_amount, 8193)

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_nic_count, 2)
        self.ins.validate_nic_count(3)
        self.ins.validate_nic_count(26)
        self.assertRaises(ValueTooHighError, self.ins.validate_nic_count, 27)

    def test_nic_type(self):
        """Test NIC valid and invalid types."""
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_nic_type, "E1000e")
        self.ins.validate_nic_type("E1000")
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_nic_type, "PCNet32")
        self.ins.validate_nic_type("virtio")
        self.ins.validate_nic_type("VMXNET3")

    def test_serial_count(self):
        """Test serial port range limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_serial_count, -1)
        self.ins.validate_serial_count(0)
        self.ins.validate_serial_count(2)
        self.assertRaises(ValueTooHighError, self.ins.validate_serial_count, 3)
