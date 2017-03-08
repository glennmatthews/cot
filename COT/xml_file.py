#!/usr/bin/env python
#
# xml_file.py - class for reading/editing/writing XML-based data
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Reading, editing, and writing XML files."""

import xml.etree.ElementTree as ET
import logging
import re

logger = logging.getLogger(__name__)


class XML(object):
    """Class capable of reading, editing, and writing XML files."""

    @staticmethod
    def get_ns(text):
        """Get the namespace prefix from an XML element or attribute name.

        Args:
          text (str): Element name or attribute name, such as
              "{http://schemas.dmtf.org/ovf/envelope/1}Element".
        Returns:
          str: "" if no prefix is present, or a namespace prefix, such as
          "http://schemas.dmtf.org/ovf/envelope/1".
        """
        match = re.match(r"\{(.*)\}", str(text))
        if not match:
            logger.error("Name '%s' has no associated namespace!", text)
            return ""
        return match.group(1)

    @staticmethod
    def strip_ns(text):
        """Remove a namespace prefix from an XML element or attribute name.

        Args:
          text (str): Element name or attribute name, such as
              "{http://schemas.dmtf.org/ovf/envelope/1}Element".
        Returns:
          str: Bare name, such as "Element".
        """
        match = re.match(r"\{.*\}(.*)", str(text))
        if not match:
            logger.error("Name '%s' has no associated namespace!", text)
            return text
        else:
            return match.group(1)

    def __init__(self, xml_file):
        """Read the given XML file and store it in memory.

        The memory representation is available as properties :attr:`tree` and
        :attr:`root`.

        Args:
          xml_file (str): File path to read.

        Raises:
          xml.etree.ElementTree.ParseError: if parsing fails
        """
        # Parse the XML into memory
        self.tree = ET.parse(xml_file)
        """:class:`xml.etree.ElementTree.ElementTree` describing this file."""
        self.root = self.tree.getroot()
        """Root :class:`xml.etree.ElementTree.Element` instance of the tree."""

    def write_xml(self, xml_file):
        """Write pretty XML out to the given file.

        Args:
          xml_file (str): Filename to write to
        """
        logger.verbose("Writing XML to %s", xml_file)

        # Pretty-print the XML for readability
        self.xml_reindent(self.root, 0)

        # We could make cleaner XML by passing "default_namespace=NSM['ovf']",
        # which will leave off the "ovf:" prefix on elements and attributes in
        # the main OVF namespace, but unfortunately, this cleaner XML is not
        # recognized as valid by ElementTree, resulting in a "write-once" OVF -
        # subsequent attempts to read and re-write the XML will give the error:
        #
        # ValueError: cannot use non-qualified names with default_namespace
        # option
        #
        # This is a bug - see http://bugs.python.org/issue17088
        self.tree.write(xml_file, xml_declaration=True, encoding='utf-8')

    @staticmethod
    def xml_reindent(parent, depth=0):
        """Recursively add indentation to XML to make it look nice.

        Args:
          parent (xml.etree.ElementTree.Element): Current parent element
          depth (int): How far down the rabbit hole we have recursed.
              Increments by 2 for each successive level of nesting.
        """
        depth += 2
        last = None
        for elem in list(parent):
            elem.tail = "\n" + (" " * depth)
            XML.xml_reindent(elem, depth)
            last = elem

        if last is not None:
            # Parent indents to first child
            parent.text = "\n" + (" " * depth)
            # Last element indents back to parent
            depth -= 2
            last.tail = "\n" + (" " * depth)

        if depth == 0:
            # Add newline at end of file
            parent.tail = "\n"

    @classmethod
    def find_child(cls, parent, tag, attrib=None, required=False):
        """Find the unique child element under the specified parent element.

        Args:
          parent (xml.etree.ElementTree.Element): Parent element
          tag (str): Child tag to match on
          attrib (dict): Child attributes to match on
          required (boolean): Whether to raise an error if no child exists

        Raises:
          LookupError: if more than one matching child is found
          KeyError: if no matching child is found and :attr:`required` is True

        Returns:
          xml.etree.ElementTree.Element: Child element found, or None
        """
        matches = cls.find_all_children(parent, tag, attrib)
        if len(matches) > 1:
            raise LookupError(
                "Found multiple matching <{0}> children (each with "
                "attributes '{1}') under <{2}>:\n{3}"
                .format(XML.strip_ns(tag),
                        attrib,
                        XML.strip_ns(parent.tag),
                        "\n".join([ET.tostring(e).decode() for e in matches])))
        elif len(matches) == 0:
            if required:
                raise KeyError("Mandatory element <{0}> not found under <{1}>"
                               .format(XML.strip_ns(tag),
                                       XML.strip_ns(parent.tag)))
            return None
        else:
            return matches[0]

    @classmethod
    def find_all_children(cls, parent, tag, attrib=None):
        """Find all matching child elements under the specified parent element.

        Args:
          parent (xml.etree.ElementTree.Element): Parent element
          tag (iterable): Child tag string (or list of tags) to match on
          attrib (dict): Child attributes to match on

        Returns:
          list: (Possibly empty) list of matching child Elements
        """
        assert parent is not None
        if isinstance(tag, str):
            elements = parent.findall(tag)
            label = tag
        else:
            elements = []
            for tag_entry in tag:
                elements.extend(parent.findall(tag_entry))
            label = [XML.strip_ns(t) for t in tag]

        if not elements:
            logger.spam("No children matching %s found under %s",
                        label, XML.strip_ns(parent.tag))
            return elements

        logger.spam("Examining %s %s elements under %s",
                    len(elements), label, XML.strip_ns(parent.tag))
        child_list = []
        for element in elements:
            found = True

            if attrib:
                for key in attrib.keys():
                    if element.get(key, None) != attrib[key]:
                        logger.spam("Attribute '%s' (%s) does not match "
                                    "expected value (%s)",
                                    XML.strip_ns(key), element.get(key, ""),
                                    attrib[key])
                        found = False
                        break

            if found:
                child_list.append(element)
        logger.spam("Found %s matching %s elements", len(child_list), label)
        return child_list

    @classmethod
    def add_child(cls, parent, new_child, ordering=None,
                  known_namespaces=None):
        """Add the given child element under the given parent element.

        Args:
          parent (xml.etree.ElementTree.Element): Parent element
          new_child (xml.etree.ElementTree.Element): Child element to attach
          ordering (list): (Optional) List describing the expected ordering of
              child tags under the parent; if a new child element is created,
              its placement under the parent will respect this sequence.
          known_namespaces (list): (Optional) List of well-understood XML
              namespaces. If a new child is created, and ``ordering`` is
              given, any tag (new or existing) that is encountered but not
              accounted for in ``ordering`` will result in COT logging a
              warning **if and only if** the unaccounted-for tag is in a
              known namespace.
        """
        if ordering and new_child.tag not in ordering:
            child_ns = XML.get_ns(new_child.tag)
            if known_namespaces and child_ns in known_namespaces:
                logger.warning("New child '%s' is in a known namespace '%s',"
                               " but is not in the list of expected children"
                               " in this namespace under '%s':\n%s",
                               XML.strip_ns(new_child.tag),
                               child_ns,
                               XML.strip_ns(parent.tag),
                               [XML.strip_ns(expected) for expected in ordering
                                if XML.get_ns(expected) == child_ns])
            # Assume this is some sort of custom element, which
            # implicitly goes at the end of the list.
            ordering = None

        if not ordering:
            parent.append(new_child)
        else:
            new_index = ordering.index(new_child.tag)
            index = 0
            found_position = False
            for child in list(parent):
                try:
                    if ordering.index(child.tag) > new_index:
                        found_position = True
                        break
                except ValueError:
                    child_ns = XML.get_ns(child.tag)
                    if known_namespaces and child_ns in known_namespaces:
                        logger.warning(
                            "Found unexpected child element '%s' under '%s' in"
                            " namespace '%s'. The list of expected children in"
                            " this namespace is only:\n%s",
                            XML.strip_ns(child.tag),
                            XML.strip_ns(parent.tag),
                            child_ns,
                            [XML.strip_ns(expected) for expected in ordering
                             if XML.get_ns(expected) == child_ns])
                    # Assume this is some sort of custom element - all known
                    # elements should implicitly come before it.
                    found_position = True
                    break
                index += 1
            if found_position:
                parent.insert(index, new_child)
            else:
                parent.append(new_child)

    @classmethod
    def set_or_make_child(cls, parent, tag, text=None, attrib=None,
                          ordering=None, known_namespaces=None):
        """Update or create a child element under the specified parent element.

        Args:
          parent (xml.etree.ElementTree.Element): Parent element
          tag (str): Child element text tag to find or create
          text (str): Value to set the child's text attribute to
          attrib (dict): Dict of child attributes to match on while
              searching and set in the final child element
          ordering (list): See :meth:`add_child`
          known_namespaces (list): See :meth:`add_child`

        Returns:
          xml.etree.ElementTree.Element: New or updated child Element.
        """
        assert parent is not None
        if attrib is None:
            attrib = {}
        element = cls.find_child(parent, tag, attrib=attrib)
        if element is None:
            logger.spam("Creating new %s element under parent %s",
                        XML.strip_ns(tag), XML.strip_ns(parent.tag))
            element = ET.Element(tag)
            XML.add_child(parent, element, ordering, known_namespaces)
        if text is not None:
            element.text = str(text)
        for attr in attrib:
            element.set(attr, attrib[attr])
        return element
