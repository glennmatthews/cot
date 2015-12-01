# platforms.py - Unit test cases for COT platform handling
#
# January 2014, Glenn F. Matthews
# Copyright (c) 2014-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for the platforms provided by COT.platforms."""

import unittest
from COT.platforms import GenericPlatform
from COT.platforms import IOSXRv, CSR1000V, IOSv, NXOSv, IOSXRvRP, IOSXRvLC
from COT.data_validation import ValueUnsupportedError
from COT.data_validation import ValueTooLowError, ValueTooHighError


class TestGenericPlatform(unittest.TestCase):
    """Test cases for generic platform handling."""

    cls = GenericPlatform

    def test_controller_type_for_device(self):
        """Test platform-specific logic for device controllers."""
        self.assertEqual(self.cls.controller_type_for_device('harddisk'),
                         'ide')
        self.assertEqual(self.cls.controller_type_for_device('cdrom'),
                         'ide')

    def test_nic_name(self):
        """Test NIC name construction."""
        self.assertEqual(self.cls.guess_nic_name(1), "Ethernet1")
        self.assertEqual(self.cls.guess_nic_name(100), "Ethernet100")

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_cpu_count, 0)
        self.cls.validate_cpu_count(1)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_memory_amount, 0)
        self.cls.validate_memory_amount(1)

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_nic_count, -1)
        self.cls.validate_nic_count(0)

    def test_serial_count(self):
        """Test serial port range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_serial_count, -1)
        self.cls.validate_serial_count(0)


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
                          self.cls.validate_nic_type, "vmxnet3")
        self.cls.validate_nic_type("e1000")
        self.cls.validate_nic_type("E1000")
        self.cls.validate_nic_type("virtio")
        self.cls.validate_nic_type("VirtIO")

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


class TestCSR1000V(unittest.TestCase):
    """Test cases for Cisco CSR 1000V platform handling."""

    cls = CSR1000V

    def test_controller_type_for_device(self):
        """Test platform-specific logic for device controllers."""
        self.assertEqual(self.cls.controller_type_for_device('harddisk'),
                         'scsi')
        self.assertEqual(self.cls.controller_type_for_device('cdrom'),
                         'ide')
        # fallthrough to parent class
        self.assertEqual(self.cls.controller_type_for_device('dvd'),
                         'ide')

    def test_nic_name(self):
        """Test NIC name construction."""
        self.assertEqual(self.cls.guess_nic_name(1),
                         "GigabitEthernet1")
        self.assertEqual(self.cls.guess_nic_name(2),
                         "GigabitEthernet2")
        self.assertEqual(self.cls.guess_nic_name(3),
                         "GigabitEthernet3")
        self.assertEqual(self.cls.guess_nic_name(4),
                         "GigabitEthernet4")

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_cpu_count, 0)
        self.cls.validate_cpu_count(1)
        self.cls.validate_cpu_count(2)
        self.assertRaises(ValueUnsupportedError,
                          self.cls.validate_cpu_count, 3)
        self.cls.validate_cpu_count(4)
        self.assertRaises(ValueTooHighError, self.cls.validate_cpu_count, 5)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError,
                          self.cls.validate_memory_amount, 2559)
        self.cls.validate_memory_amount(2560)
        self.cls.validate_memory_amount(8192)
        self.assertRaises(ValueTooHighError,
                          self.cls.validate_memory_amount, 8193)

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_nic_count, 2)
        self.cls.validate_nic_count(3)
        self.cls.validate_nic_count(26)
        self.assertRaises(ValueTooHighError, self.cls.validate_nic_count, 27)

    def test_nic_type(self):
        """Test NIC valid and invalid types."""
        self.cls.validate_nic_type("vmxnet3")
        self.cls.validate_nic_type("VMXNET3")
        self.cls.validate_nic_type("e1000")
        self.cls.validate_nic_type("E1000")
        self.cls.validate_nic_type("virtio")
        self.cls.validate_nic_type("VirtIO")

    def test_serial_count(self):
        """Test serial port range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_serial_count, -1)
        self.cls.validate_serial_count(0)
        self.cls.validate_serial_count(2)
        self.assertRaises(ValueTooHighError, self.cls.validate_serial_count, 3)


class TestIOSv(unittest.TestCase):
    """Test cases for Cisco IOSv platform handling."""

    cls = IOSv

    def test_nic_name(self):
        """Test NIC name construction."""
        self.assertEqual(self.cls.guess_nic_name(1),
                         "GigabitEthernet0/0")
        self.assertEqual(self.cls.guess_nic_name(2),
                         "GigabitEthernet0/1")
        self.assertEqual(self.cls.guess_nic_name(3),
                         "GigabitEthernet0/2")
        self.assertEqual(self.cls.guess_nic_name(4),
                         "GigabitEthernet0/3")

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_cpu_count, 0)
        self.cls.validate_cpu_count(1)
        self.assertRaises(ValueTooHighError, self.cls.validate_cpu_count, 2)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError,
                          self.cls.validate_memory_amount, 191)
        self.cls.validate_memory_amount(192)
        self.cls.validate_memory_amount(3072)
        self.assertRaises(ValueTooHighError,
                          self.cls.validate_memory_amount, 3073)

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_nic_count, -1)
        self.cls.validate_nic_count(0)
        self.cls.validate_nic_count(16)
        self.assertRaises(ValueTooHighError, self.cls.validate_nic_count, 17)

    def test_nic_type(self):
        """Test NIC valid and invalid types."""
        self.assertRaises(ValueUnsupportedError,
                          self.cls.validate_nic_type, "vmxnet3")
        self.assertRaises(ValueUnsupportedError,
                          self.cls.validate_nic_type, "virtio")
        self.cls.validate_nic_type("e1000")
        self.cls.validate_nic_type("E1000")

    def test_serial_count(self):
        """Test serial port range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_serial_count, 0)
        self.cls.validate_serial_count(1)
        self.cls.validate_serial_count(2)
        self.assertRaises(ValueTooHighError, self.cls.validate_serial_count, 3)


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
                          self.cls.validate_nic_type, "vmxnet3")
        self.cls.validate_nic_type("e1000")
        self.cls.validate_nic_type("E1000")
        self.cls.validate_nic_type("virtio")
        self.cls.validate_nic_type("VirtIO")

    def test_serial_count(self):
        """Test serial port range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_serial_count, 0)
        self.cls.validate_serial_count(1)
        self.cls.validate_serial_count(2)
        self.assertRaises(ValueTooHighError, self.cls.validate_serial_count, 3)
