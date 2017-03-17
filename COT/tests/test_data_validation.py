#!/usr/bin/env python
#
# data_validation.py - Unit test cases for COT.data_validation module
#
# December 2014, Glenn F. Matthews
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

"""Unit test cases for COT.data_validation module."""

import re

from COT.data_validation import (
    match_or_die, file_checksum,
    canonicalize_helper, canonicalize_nic_subtype, NIC_TYPES,
    mac_address, device_address, no_whitespace, truth_value,
    validate_int, non_negative_int, positive_int,
    InvalidInputError, ValueMismatchError, ValueUnsupportedError,
    ValueTooLowError, ValueTooHighError,
)
from COT.tests import COTTestCase


class TestFileChecksum(COTTestCase):
    """Test cases for file_checksum() function."""

    def test_file_checksum_md5(self):
        """Test case for file_checksum() with md5 sum."""
        checksum = file_checksum(self.input_ovf, 'md5')
        self.assertEqual(checksum, "4e7a3ba0b70f6784a3a91b18336296c7")

        checksum = file_checksum(self.minimal_ovf, 'md5')
        self.assertEqual(checksum, "288e1e3fcb05265cd9b8c7578e173fef")

    def test_file_checksum_sha1(self):
        """Test case for file_checksum() with sha1 sum."""
        checksum = file_checksum(self.input_ovf, 'sha1')
        self.assertEqual(checksum, "c3bd2579c2edc76ea35b5bde7d4f4e41eab08963")

        checksum = file_checksum(self.minimal_ovf, 'sha1')
        self.assertEqual(checksum,
                         "5d0635163f6a580442f01466245e122f8412e8d6")

    def test_file_checksum_unsupported(self):
        """Test invalid options to file_checksum()."""
        self.assertRaises(NotImplementedError,
                          file_checksum,
                          self.input_ovf,
                          'sha256')
        self.assertRaises(NotImplementedError,
                          file_checksum,
                          self.input_ovf,
                          'crc')


class TestValidationFunctions(COTTestCase):
    """Test cases for input validation APIs."""

    def test_canonicalize_helper(self):
        """Test the canonicalize_helper() function."""
        mappings = [
            ("lsi *logic *sas", 'lsilogicsas'),
            ("lsi *logic", 'lsilogic'),
            ("[fF]oo[0-9]+[bB]ar", 'FooBar'),
        ]
        # not case-insensitive by default
        with self.assertRaises(ValueUnsupportedError) as catcher:
            canonicalize_helper("foo", "LSI Logic SAS", mappings)
        self.assertEqual(catcher.exception.value_type, "foo")
        self.assertEqual(catcher.exception.expected_value,
                         ["lsilogicsas", "lsilogic", "FooBar"])

        # but can be case-insensitive on request
        self.assertEqual(canonicalize_helper("", "LSI Logic SAS",
                                             mappings, re.IGNORECASE),
                         "lsilogicsas")

        # mappings are checked in order
        self.assertEqual(canonicalize_helper("", "lsilogics",
                                             mappings, re.IGNORECASE),
                         "lsilogic")
        # mappings are regexps
        self.assertEqual(canonicalize_helper("", "foo123bar",
                                             mappings),
                         "FooBar")
        # special cases
        self.assertEqual(canonicalize_helper("", "", mappings), None)
        self.assertEqual(canonicalize_helper("", None, mappings), None)

    def test_nic_types_idempotence(self):
        """Test the canonicalize_nic_subtype() function.

        Verify that the NIC_TYPES / _NIC_MAPPINGS are idempotent.
        """
        for nictype in NIC_TYPES:
            self.assertEqual(canonicalize_nic_subtype(nictype), nictype)

    def test_match_or_die(self):
        """Test the match_or_die() function."""
        with self.assertRaises(ValueMismatchError) as catcher:
            match_or_die("input", "a", "output", "b")
        self.assertEqual(str(catcher.exception),
                         "input a does not match output b")

        match_or_die("input", "a", "output", "a")

    def test_mac_address(self):
        """Test the mac_address() validator."""
        for valid_string in ["01:08:ab:cd:e0:f9", "00-00-00-00-00-00",
                             "081a.1357.ffff", " 01:02:03:04:05:06 "]:
            self.assertEqual(mac_address(valid_string), valid_string.strip())

        for invalid_string in ["01:08:ab:cd:e0:g9", "01:02:03:04:05",
                               "00:00-00:00-00:00", "1111.2345",
                               "01-02-03-04-05", "01-02-03-04-05-06-07",
                               "12345.6789.abcd"]:
            self.assertRaises(InvalidInputError, mac_address, invalid_string)

    def test_device_address(self):
        """Test the device_address() validator."""
        for valid_string in ["0:0", "1:1", "3:7", "1:10", " 2:3 "]:
            self.assertEqual(device_address(valid_string),
                             valid_string.strip())

        for invalid_string in ["0", "-1:0", "1:-1", "1:1:1", "1:a"]:
            self.assertRaises(InvalidInputError,
                              device_address, invalid_string)

    def test_no_whitespace(self):
        """Test the no_whitespace() validator."""
        for valid_string in ["", "a", " a ",
                             "abcdefghijklmnopqrstuvwxyz1234567890"]:
            self.assertEqual(no_whitespace(valid_string), valid_string.strip())

        for invalid_string in ["a b", "a\tb" "a\nb" "a\rb"]:
            self.assertRaises(InvalidInputError, no_whitespace, invalid_string)

    def test_validate_int(self):
        """Test the validate_int() validator."""
        for valid_string in ["1", "08", "123", " 256 ", "-10"]:
            self.assertEqual(validate_int(valid_string), int(valid_string))

        self.assertEqual(256, validate_int("256", minimum=128, maximum=512))
        self.assertEqual(256, validate_int("256", minimum=256))
        self.assertEqual(256, validate_int("256", maximum=256))
        self.assertRaises(ValueUnsupportedError, validate_int, "a")
        self.assertRaises(ValueTooLowError, validate_int, "10", minimum=11)
        self.assertRaises(ValueTooLowError, validate_int, "-1", minimum=0)
        self.assertRaises(ValueTooHighError, validate_int, "10", maximum=9)
        self.assertRaises(ValueTooHighError, validate_int, "1", maximum=0)

    def test_non_negative_int(self):
        """Test the non_negative_int() validator."""
        self.assertEqual(non_negative_int("10"), 10)
        self.assertEqual(non_negative_int("0"), 0)
        self.assertRaises(ValueTooLowError, non_negative_int, "-1")

    def test_positive_int(self):
        """Test the positive_int() validator."""
        self.assertEqual(positive_int("10"), 10)
        self.assertRaises(ValueTooLowError, positive_int, "0")

    def test_truth_value(self):
        """Test the truth_value() validator."""
        self.assertTrue(truth_value('y'))
        self.assertFalse(truth_value('n'))
        self.assertRaises(ValueUnsupportedError, truth_value, "foo")

    def test_custom_error_attributes(self):
        """Test the properties of ValueUnsupportedError and its children."""
        with self.assertRaises(ValueUnsupportedError) as catcher:
            validate_int("a")
        self.assertEqual(catcher.exception.value_type, "input")
        self.assertEqual(catcher.exception.actual_value, "a")
        self.assertEqual(catcher.exception.expected_value, "integer")
        self.assertEqual(str(catcher.exception),
                         "Unsupported value 'a' for input - expected integer")

        with self.assertRaises(ValueTooLowError) as catcher:
            non_negative_int(-1)
        self.assertEqual(catcher.exception.value_type, "input")
        self.assertEqual(catcher.exception.actual_value, -1)
        self.assertEqual(catcher.exception.expected_value, 0)
        self.assertEqual(
            str(catcher.exception),
            "Value '-1' for input is too low - must be at least 0")

        with self.assertRaises(ValueTooHighError) as catcher:
            validate_int("100", maximum=10, label="score")
        self.assertEqual(catcher.exception.value_type, "score")
        self.assertEqual(catcher.exception.actual_value, 100)
        self.assertEqual(catcher.exception.expected_value, 10)
        self.assertEqual(
            str(catcher.exception),
            "Value '100' for score is too high - must be at most 10")
