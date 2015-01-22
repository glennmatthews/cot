#!/usr/bin/env python
#
# data_validation.py - Unit test cases for COT.data_validation module
#
# December 2014, Glenn F. Matthews
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

import unittest

from COT.data_validation import mac_address, device_address, no_whitespace
from COT.data_validation import validate_int, non_negative_int, positive_int
from COT.data_validation import InvalidInputError, ValueUnsupportedError
from COT.data_validation import ValueTooLowError, ValueTooHighError


class TestValidationFunctions(unittest.TestCase):
    """Test cases for input validation APIs."""

    def test_mac_address(self):
        for valid_string in ["01:08:ab:cd:e0:f9", "00-00-00-00-00-00",
                             "081a.1357.ffff", " 01:02:03:04:05:06 "]:
            self.assertEqual(mac_address(valid_string), valid_string.strip())

        for invalid_string in ["01:08:ab:cd:e0:g9", "01:02:03:04:05",
                               "00:00-00:00-00:00", "1111.2345",
                               "01-02-03-04-05", "01-02-03-04-05-06-07",
                               "12345.6789.abcd"]:
            self.assertRaises(InvalidInputError, mac_address, invalid_string)

    def test_device_address(self):
        for valid_string in ["0:0", "1:1", "3:7", "1:10", " 2:3 "]:
            self.assertEqual(device_address(valid_string),
                             valid_string.strip())

        for invalid_string in ["0", "-1:0", "1:-1", "1:1:1", "1:a"]:
            self.assertRaises(InvalidInputError,
                              device_address, invalid_string)

    def test_no_whitespace(self):
        for valid_string in ["", "a", " a ",
                             "abcdefghijklmnopqrstuvwxyz1234567890"]:
            self.assertEqual(no_whitespace(valid_string), valid_string.strip())

        for invalid_string in ["a b", "a\tb" "a\nb" "a\rb"]:
            self.assertRaises(InvalidInputError, no_whitespace, invalid_string)

    def test_validate_int(self):
        for valid_string in ["1", "08", "123", " 256 ", "-10"]:
            self.assertEqual(validate_int(valid_string), int(valid_string))

        self.assertEqual(256, validate_int("256", min=128, max=512))
        self.assertEqual(256, validate_int("256", min=256))
        self.assertEqual(256, validate_int("256", max=256))
        self.assertRaises(ValueUnsupportedError, validate_int, "a")
        self.assertRaises(ValueTooLowError, validate_int, "10", min=11)
        self.assertRaises(ValueTooLowError, validate_int, "-1", min=0)
        self.assertRaises(ValueTooHighError, validate_int, "10", max=9)
        self.assertRaises(ValueTooHighError, validate_int, "1", max=0)

    def test_non_negative_int(self):
        self.assertEqual(non_negative_int("10"), 10)
        self.assertEqual(non_negative_int("0"), 0)
        self.assertRaises(ValueTooLowError, non_negative_int, "-1")

    def test_positive_int(self):
        self.assertEqual(positive_int("10"), 10)
        self.assertRaises(ValueTooLowError, positive_int, "0")
