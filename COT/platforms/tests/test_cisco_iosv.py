# test_cisco_iosv.py - Unit test cases for Cisco IOSv platform
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

"""Unit test cases for IOSv platform."""

import unittest
import logging
# Make sure there's always a "no-op" logging handler.
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        """No-op logging handler."""

        def emit(self, record):
            """Do nothing.

            Args:
              record (object): Ignored.
            """
            pass

from COT.platforms.cisco_iosv import IOSv
from COT.data_validation import (
    ValueUnsupportedError, ValueTooLowError, ValueTooHighError
)

logging.getLogger('COT').addHandler(NullHandler())

# pylint: disable=missing-type-doc,missing-param-doc


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
                          self.cls.validate_nic_type, "E1000e")
        self.cls.validate_nic_type("E1000")
        self.assertRaises(ValueUnsupportedError,
                          self.cls.validate_nic_type, "PCNet32")
        self.assertRaises(ValueUnsupportedError,
                          self.cls.validate_nic_type, "virtio")
        self.assertRaises(ValueUnsupportedError,
                          self.cls.validate_nic_type, "VMXNET3")

    def test_serial_count(self):
        """Test serial port range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_serial_count, 0)
        self.cls.validate_serial_count(1)
        self.cls.validate_serial_count(2)
        self.assertRaises(ValueTooHighError, self.cls.validate_serial_count, 3)
