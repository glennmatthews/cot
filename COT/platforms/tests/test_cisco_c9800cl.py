# test_cisco_c9800cl.py - Unit test cases for Cisco C9800-CL platform
#
# February 2019, Subba Srinivas
# Copyright (c) 2019 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for C9800-CL platform."""

from COT.platforms.cisco_c9800cl import C9800CL
from COT.data_validation import (
    ValueUnsupportedError, ValueTooLowError, ValueTooHighError
)
from COT.platforms.tests import PlatformTests


class TestC9800CL(PlatformTests.PlatformTest):
    """Test cases for Cisco C9800CL platform handling."""

    cls = C9800CL
    product_string = "com.cisco.vwlc"

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

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_cpu_count, 0)
        self.assertRaises(ValueTooLowError, self.ins.validate_cpu_count, 3)
        self.ins.validate_cpu_count(4)
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_cpu_count, 5)
        self.ins.validate_cpu_count(6)
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_cpu_count, 7)
        self.ins.validate_cpu_count(10)
        self.assertRaises(ValueTooHighError, self.ins.validate_cpu_count, 11)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError,
                          self.ins.validate_memory_amount, 8191)
        self.ins.validate_memory_amount(8192)
        self.ins.validate_memory_amount(32768)
        self.assertRaises(ValueTooHighError,
                          self.ins.validate_memory_amount, 32769)

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_nic_count, 0)
        self.ins.validate_nic_count(1)
        self.ins.validate_nic_count(2)
        self.assertRaises(ValueTooHighError, self.ins.validate_nic_count, 4)

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
