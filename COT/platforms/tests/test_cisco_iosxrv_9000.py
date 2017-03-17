# test_cisco_iosxrv_9000.py - Unit test cases for Cisco IOS XRv9k platform
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

"""Unit test cases for IOSXRv9000 class."""

from COT.platforms.cisco_iosxrv_9000 import IOSXRv9000
from COT.data_validation import (
    ValueUnsupportedError, ValueTooLowError, ValueTooHighError
)
from COT.platforms.tests import PlatformTests


class TestIOSXRv9000(PlatformTests.PlatformTest):
    """Test cases for Cisco IOS XRv 9000 platform handling."""

    cls = IOSXRv9000
    product_string = "com.cisco.ios-xrv9000"

    def test_nic_name(self):
        """Test NIC name construction."""
        self.assertEqual(self.ins.guess_nic_name(1),
                         "MgmtEth0/0/CPU0/0")
        self.assertEqual(self.ins.guess_nic_name(2),
                         "CtrlEth")
        self.assertEqual(self.ins.guess_nic_name(3),
                         "DevEth")
        self.assertEqual(self.ins.guess_nic_name(4),
                         "GigabitEthernet0/0/0/0")
        self.assertEqual(self.ins.guess_nic_name(5),
                         "GigabitEthernet0/0/0/1")

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_cpu_count, 0)
        self.ins.validate_cpu_count(1)
        self.ins.validate_cpu_count(32)
        self.assertRaises(ValueTooHighError, self.ins.validate_cpu_count, 33)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError,
                          self.ins.validate_memory_amount, 8191)
        self.ins.validate_memory_amount(8192)
        self.ins.validate_memory_amount(32768)
        self.ins.validate_memory_amount(128 * 1024)

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_nic_count, 0)
        self.assertRaises(ValueTooLowError, self.ins.validate_nic_count, 3)
        self.ins.validate_nic_count(4)
        self.ins.validate_nic_count(32)
        # No upper bound known at present

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
        self.assertRaises(ValueTooLowError, self.ins.validate_serial_count, 0)
        self.ins.validate_serial_count(1)
        self.ins.validate_serial_count(4)
        self.assertRaises(ValueTooHighError, self.ins.validate_serial_count, 5)
