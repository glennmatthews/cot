#!/usr/bin/env python
#
# data_validation.py - Helper libraries to validate data sanity
#
# September 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

import xml.etree.ElementTree as ET
import sys
import re

def to_string(obj):
    """String representation of an object. Has special-case handling for XML
    ElementTree objects"""
    if isinstance(obj, ET.Element):
        return ET.tostring(obj)
    else:
        return str(obj)


def natural_sort(l):
    """Sort the given list "naturally" rather than in ASCII order.
    E.g, "10" comes after "9" rather than between "1" and "2".
    See also http://nedbatchelder.com/blog/200712/human_sorting.html
    """
    # Convert number strings to ints, leave other strings as text
    convert = lambda text: int(text) if text.isdigit() else text
    # Split the key into a list of [text, int, text, int, ...]
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
    # Sort based on alphanum_key
    return sorted(l, key=alphanum_key)


def match_or_die(first_label, first, second_label, second):
    """If "first" and "second" do not match exactly, die!"""
    if first != second:
        raise ValueMismatchError("{0} {1} does not match {2} {3}"
                                 .format(first_label,
                                         to_string(first),
                                         second_label,
                                         to_string(second)))


def check_for_conflict(label, li):
    """Make sure all references in the list either point to the same element
       or point to None. Returns the object or None"""
    obj = None
    for i, obj1 in enumerate(li):
        if obj1 is None:
            continue
        for obj2 in li[(i+1):]:
            if obj2 is not None and obj1 != obj2:
                raise ValueMismatchError(
                    "Found multiple candidates for the {0}: "
                    "\n{1}\n...and...\n{2}\nPlease correct or clarify "
                    "your search parameters."
                    .format(label, to_string(obj1), to_string(obj2)))
        obj = obj1
    return obj

# Some handy exception and error types we can throw
class ValueMismatchError(ValueError):
    """Error class indicating that values which were expected to be equal
    turned out to be not equal.
    """
    pass

class ValueUnsupportedError(ValueError):
    """Error class indicating an unsupported value was provided.

    Attributes:
        value_type -- descriptive string
        actual_value -- value provided
        expected_value -- expected value or values (item or list)
    """
    def __init__(self, value_type, actual, expected):
        self.value_type = value_type
        self.actual_value = actual
        self.expected_value = expected

    def __str__(self):
        return ("Unsupported value '{0}' for {1} - expected {2}"
                .format(self.actual_value, self.value_type,
                        self.expected_value))

class ValueTooLowError(ValueUnsupportedError):
    """Error class indicating a number lower than the lowest supported value.

    Attributes:
        value_type -- descriptive string
        actual_value -- value provided
        expected_value -- minimum supported value
    """
    def __str__(self):
        return ("Value '{0}' for {1} is too low - must be at least {2}"
                .format(self.actual_value, self.value_type,
                        self.expected_value))


class ValueTooHighError(ValueUnsupportedError):
    """Error class indicating a number higher than the highest supported value.

    Attributes:
        value_type -- descriptive string
        actual_value -- value provided
        expected_value -- maximum supported value
    """
    def __str__(self):
        return ("Value '{0}' for {1} is too high - must be at most {2}"
                .format(self.actual_value, self.value_type,
                        self.expected_value))
