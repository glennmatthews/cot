# xml_file.py - Unit test cases for generic XML file class
#
# January 2015, Glenn F. Matthews
# Copyright (c) 2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for the COT.xml_file.XML class."""

import unittest
from pkg_resources import resource_filename

from COT.xml_file import XML


class TestXMLClass(unittest.TestCase):
    """Test cases for XML class methods."""

    def test_get_ns(self):
        """Test the get_ns() function."""
        self.assertEqual(
            "http://schemas.dmtf.org/ovf/envelope/1",
            XML.get_ns("{http://schemas.dmtf.org/ovf/envelope/1}required"))
        self.assertEqual(
            "",
            XML.get_ns("required"))

    def test_strip_ns(self):
        """Test the strip_ns() function."""
        self.assertEqual(
            "required",
            XML.strip_ns("{http://schemas.dmtf.org/ovf/envelope/1}required"))
        self.assertEqual(
            "required",
            XML.strip_ns("required"))


class TestXMLInstance(unittest.TestCase):
    """Test cases for XML instance methods."""

    OVF = "{http://schemas.dmtf.org/ovf/envelope/1}"

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.xml = XML()
        self.xml.read_xml(resource_filename(__name__, "input.ovf"))
        super(TestXMLInstance, self).setUp()

    def test_find_child(self):
        """Test corner cases of the find_child() method."""
        match = self.xml.find_child(self.xml.root,
                                    self.OVF + "References")
        self.assertEqual(match.tag, self.OVF + "References")

        # multiple children -> LookupError
        self.assertRaises(LookupError,
                          self.xml.find_child,
                          match,
                          self.OVF + "File")

        # no such child -> None unless required
        match = self.xml.find_child(self.xml.root,
                                    self.OVF + "Foobar")
        self.assertEqual(None, match)

        # no such child -> KeyError if required
        self.assertRaises(KeyError,
                          self.xml.find_child,
                          self.xml.root,
                          self.OVF + "Foobar",
                          required=True)

    def test_set_or_make_child(self):
        """Call set_or_make_child() in some slightly incorrect ways."""
        # Trigger the warning in add_child() logged when
        # creating a new child that's in a known namespace
        # but the child isn't in the expected ordering
        self.xml.set_or_make_child(
            self.xml.root,
            self.OVF + "foo",
            ordering=[self.OVF + "References"],
            known_namespaces=["http://schemas.dmtf.org/ovf/envelope/1"]
        )

        # Trigger the warning in add_child() logged when
        # creating a new child in a known namespace
        # with an expected ordering that includes the child,
        # but other children in this namespace are left out.
        self.xml.set_or_make_child(
            self.xml.root,
            self.OVF + "bar",
            ordering=[self.OVF + "DiskSection",
                      self.OVF + "bar"],
            known_namespaces=["http://schemas.dmtf.org/ovf/envelope/1"]
        )
