# test_cisco_iosxrv.py - Unit test cases for Cisco IOS XRv platform handling
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

"""Unit test cases for IOSXRv class and its subclasses."""

import unittest
from COT.platforms.cisco_iosxrv import IOSXRv, IOSXRvRP, IOSXRvLC
from COT.data_validation import (
    ValueUnsupportedError, ValueTooLowError, ValueTooHighError
)


class TestIOSXRv(unittest.TestCase):
    """Test cases for Cisco IOS XRv platform handling."""

    cls = IOSXRv

    def test_nic_name(self):
        """Test NIC name construction."""
        self.assertEqual(self.cls.guess_nic_name(1),
                         "MgmtEth0/0/CPU0/0")
        self.assertEqual(self.cls.guess_nic_name(2),
                         "GigabitEthernet0/0/0/0")
        self.assertEqual(self.cls.guess_nic_name(3),
                         "GigabitEthernet0/0/0/1")
        self.assertEqual(self.cls.guess_nic_name(4),
                         "GigabitEthernet0/0/0/2")

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_cpu_count, 0)
        self.cls.validate_cpu_count(1)
        self.cls.validate_cpu_count(8)
        self.assertRaises(ValueTooHighError, self.cls.validate_cpu_count, 9)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError,
                          self.cls.validate_memory_amount, 3071)
        self.cls.validate_memory_amount(3072)
        self.cls.validate_memory_amount(8192)
        self.assertRaises(ValueTooHighError,
                          self.cls.validate_memory_amount, 8193)

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_nic_count, 0)
        self.cls.validate_nic_count(1)
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
        self.cls.validate_serial_count(4)
        self.assertRaises(ValueTooHighError, self.cls.validate_serial_count, 5)


class TestIOSXRvRP(TestIOSXRv):
    """Test cases for Cisco IOS XRv HA-capable RP platform handling."""

    cls = IOSXRvRP

    # Inherit all test cases from IOSXRv class, except where overridden below:

    def test_nic_name(self):
        """Test NIC name construction.

        An HA-capable RP has a fabric interface in addition to the usual
        MgmtEth NIC, but does not have GigabitEthernet NICs.
        """
        self.assertEqual(self.cls.guess_nic_name(1),
                         "fabric")
        self.assertEqual(self.cls.guess_nic_name(2),
                         "MgmtEth0/{SLOT}/CPU0/0")

    def test_nic_count(self):
        """Test NIC range limits. Only fabric+MgmtEth is allowed."""
        self.assertRaises(ValueTooLowError, self.cls.validate_nic_count, 0)
        self.cls.validate_nic_count(1)
        self.cls.validate_nic_count(2)
        self.assertRaises(ValueTooHighError, self.cls.validate_nic_count, 3)


class TestIOSXRvLC(TestIOSXRv):
    """Test cases for Cisco IOS XRv line card platform handling."""

    cls = IOSXRvLC

    # Inherit all test cases from IOSXRv class, except where overridden below:

    def test_nic_name(self):
        """Test NIC name construction.

        An LC has a fabric but no MgmtEth.
        """
        self.assertEqual(self.cls.guess_nic_name(1),
                         "fabric")
        self.assertEqual(self.cls.guess_nic_name(2),
                         "GigabitEthernet0/{SLOT}/0/0")
        self.assertEqual(self.cls.guess_nic_name(3),
                         "GigabitEthernet0/{SLOT}/0/1")
        self.assertEqual(self.cls.guess_nic_name(4),
                         "GigabitEthernet0/{SLOT}/0/2")

    def test_serial_count(self):
        """Test serial port range limits.

        An LC with zero serial ports is valid.
        """
        self.cls.validate_serial_count(0)
        self.cls.validate_serial_count(4)
        self.assertRaises(ValueTooHighError, self.cls.validate_serial_count, 5)
