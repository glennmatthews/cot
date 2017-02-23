# test_cisco_nxosv.py - Unit test cases for Cisco Nexus 9000v platform
#
# January 2017, Glenn F. Matthews
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

"""Unit test cases for Nexus 9000v platform."""

from COT.platforms.cisco_nexus_9000v import Nexus9000v
from COT.data_validation import (
    ValueUnsupportedError, ValueTooLowError, ValueTooHighError
)
from COT.platforms.tests import PlatformTests


class TestNexus9000v(PlatformTests.PlatformTest):
    """Test cases for Cisco Nexus 9000v platform handling."""

    cls = Nexus9000v
    product_string = "com.cisco.n9k"

    def test_nic_name(self):
        """Test NIC name construction."""
        self.assertEqual(self.ins.guess_nic_name(1),
                         "mgmt0")
        self.assertEqual(self.ins.guess_nic_name(2),
                         "Ethernet1/1")
        self.assertEqual(self.ins.guess_nic_name(3),
                         "Ethernet1/2")
        self.assertEqual(self.ins.guess_nic_name(4),
                         "Ethernet1/3")

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_cpu_count, 0)
        self.ins.validate_cpu_count(1)
        self.ins.validate_cpu_count(4)
        self.assertRaises(ValueTooHighError, self.ins.validate_cpu_count, 5)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError,
                          self.ins.validate_memory_amount, 8191)
        self.ins.validate_memory_amount(8192)
        self.ins.validate_memory_amount(16384)
        # No upper bound known at present

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_nic_count, 0)
        self.ins.validate_nic_count(1)
        self.ins.validate_nic_count(65)
        self.assertRaises(ValueTooHighError, self.ins.validate_nic_count, 66)

    def test_nic_type(self):
        """Test NIC valid and invalid types."""
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_nic_type, "E1000e")
        self.ins.validate_nic_type("E1000")
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_nic_type, "PCNet32")
        self.assertRaises(ValueUnsupportedError,
                          self.ins.validate_nic_type, "virtio")
        self.ins.validate_nic_type("VMXNET3")

    def test_serial_count(self):
        """Test serial port range limits."""
        self.assertRaises(ValueTooLowError, self.ins.validate_serial_count, 0)
        self.ins.validate_serial_count(1)
        self.assertRaises(ValueTooHighError, self.ins.validate_serial_count, 2)
