# test_cisco_iosv.py - Unit test cases for Cisco IOSv platform
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

"""Unit test cases for IOSv platform."""

from COT.platforms.cisco_iosv import IOSv
from COT.data_validation import (
    ValueUnsupportedError, ValueTooLowError, ValueTooHighError
)
from COT.platforms.tests import PlatformTests

# pylint: disable=missing-type-doc,missing-param-doc


class TestIOSv(PlatformTests.PlatformTest):
    """Test cases for Cisco IOSv platform handling."""

    cls = IOSv
    product_string = "com.cisco.iosv"

    def test_nic_name(self):
        """Test NIC name construction."""
        self.assertEqual(self.ins.guess_nic_name(1),
                         "GigabitEthernet0/0")
        self.assertEqual(self.ins.guess_nic_name(2),
                         "GigabitEthernet0/1")
        self.assertEqual(self.ins.guess_nic_name(3),
                         "GigabitEthernet0/2")
        self.assertEqual(self.ins.guess_nic_name(4),
                         "GigabitEthernet0/3")

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_cpu_count, 0)
        self.ins.validate_cpu_count(1)
        self.assertRaises(ValueTooHighError, self.ins.validate_cpu_count, 2)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError,
                          self.ins.validate_memory_amount, 191)
        self.ins.validate_memory_amount(192)
        self.assertLogged(levelname="WARNING",
                          msg="RAM may not be sufficient")
        self.ins.validate_memory_amount(383)
        self.assertLogged(levelname="WARNING",
                          msg="RAM may not be sufficient")
        # no log expected at or above 384 MiB
        self.ins.validate_memory_amount(384)
        self.ins.validate_memory_amount(3072)
        self.assertRaises(ValueTooHighError,
                          self.ins.validate_memory_amount, 3073)

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_nic_count, -1)
        self.ins.validate_nic_count(0)
        self.ins.validate_nic_count(16)
        self.assertRaises(ValueTooHighError, self.ins.validate_nic_count, 17)

    def test_nic_type(self):
        """Test NIC valid and invalid types."""
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_nic_type, "E1000e")
        self.ins.validate_nic_type("E1000")
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_nic_type, "PCNet32")
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_nic_type, "virtio")
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_nic_type, "VMXNET3")

    def test_serial_count(self):
        """Test serial port range limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_serial_count, 0)
        self.ins.validate_serial_count(1)
        self.ins.validate_serial_count(2)
        self.assertRaises(ValueTooHighError, self.ins.validate_serial_count, 3)
