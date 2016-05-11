#!/usr/bin/env python
#
# xml_file.py - class for reading/editing/writing XML-based data
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2015 the COT project developers.
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
import sys

logger = logging.getLogger(__name__)


class XML(object):
    """Class capable of reading, editing, and writing XML files."""

    @classmethod
    def get_ns(cls, text):
        """Get the namespace prefix from an XML element or attribute name."""
        match = re.match(r"\{(.*)\}", str(text))
        if not match:
            logger.error("No namespace prefix on {0}??".format(text))
            return ""
        return match.group(1)

    @classmethod
    def strip_ns(cls, text):
        """Remove a namespace prefix from an XML element or attribute name."""
        match = re.match(r"\{.*\}(.*)", str(text))
        if match is None:
            logger.error("No namespace prefix on {0}??".format(text))
            return text
        else:
            return match.group(1)

    def read_xml(self, xml_file):
        """Read the given XML file and store it in memory.

        The memory representation is available as :attr:`self.tree` and
        :attr:`self.root`.

        :raise xml.etree.ElementTree.ParseError: if parsing fails under Python
          2.7 or later
        :raise xml.parsers.expat.ExpatError: if parsing fails under Python 2.6
        :param str xml_file: File path to read.
        """
        # Parse the XML into memory
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()

    def register_namespace(self, prefix, URI):
        """Record a particular mapping between a namespace prefix and URI.

        :param str prefix: Namespace prefix such as "ovf"
        :param str URI: Namespace URI such as
          "http://schemas.dmtf.org/ovf/envelope/1"
        """
        try:
            ET.register_namespace(prefix, URI)
        except AttributeError:
            # 2.6 doesn't have the above API so we must write directly
            ET._namespace_map[URI] = prefix

    def write_xml(self, file):
        """Write pretty XML out to the given file.

        :param str file: Filename to write to
        """
        logger.debug("Writing XML to {0}".format(file))

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
        if sys.hexversion >= 0x02070000:
            self.tree.write(file, xml_declaration=True, encoding='utf-8')
        else:
            # 2.6 doesn't have the xml_declaration parameter. Sigh.
            self.tree.write(file, encoding='utf-8')

    def xml_reindent(self, parent, depth):
        """Recursively add indentation to XML to make it look nice.

        :param xml.etree.ElementTree.Element parent: Current parent element
        :param int depth: How far down the rabbit hole we have recursed.
           Increments by 2 for each successive level of nesting.
        """
        depth += 2
        last = None
        for elem in list(parent):
            elem.tail = "\n" + (" " * depth)
            self.xml_reindent(elem, depth)
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
    def find_child(cls, parent, tag, attrib={}, required=False):
        """Find the unique child element under the specified parent element.

        :raises LookupError: if more than one matching child is found
        :raises KeyError: if no matching child is found and :attr:`required`
          is True
        :param xml.etree.ElementTree.Element parent: Parent element
        :param str tag: Child tag to match on
        :param dict attrib: Child attributes to match on
        :param boolean required: Whether to raise an error if no child exists
        :rtype: xml.etree.ElementTree.Element
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
    def find_all_children(cls, parent, tag, attrib={}):
        """Find all matching child elements under the specified parent element.

        :param xml.etree.ElementTree.Element parent: Parent element
        :param str tag: Child tag to match on
        :param dict attrib: Child attributes to match on
        :rtype: list of xml.etree.ElementTree.Element instances
        """
        assert parent is not None
        elements = parent.findall(tag)
        logger.debug("Examining {0} {1} elements under {2}"
                     .format(len(elements), XML.strip_ns(tag),
                             XML.strip_ns(parent.tag)))
        list = []
        for e in elements:
            found = True

            for key in attrib.keys():
                if e.get(key, None) != attrib[key]:
                    logger.debug("Attribute '{0}' ({1}) does not match "
                                 "expected value ({2})"
                                 .format(XML.strip_ns(key), e.get(key, ""),
                                         attrib[key]))
                    found = False
                    break

            if found:
                list.append(e)
        logger.debug("Found {0} matching {1} elements"
                     .format(len(list), XML.strip_ns(tag)))
        return list

    @classmethod
    def add_child(cls, parent, new_child, ordering=None,
                  known_namespaces=None):
        """Add the given child element under the given parent element.

        :param xml.etree.ElementTree.Element parent: Parent element
        :param xml.etree.ElementTree.Element new_child: Child element to attach
        :param list ordering: (Optional) List describing the expected ordering
           of child tags under the parent; if a new child element is created,
           its placement under the parent will respect this sequence.
        :param list known_namespaces: (Optional) List of well-understood XML
           namespaces. If a new child is created, and ``ordering`` is given,
           any tag (new or existing) that is encountered but not accounted for
           in ``ordering`` will result in COT logging a warning **iff** the
           unaccounted-for tag is in a known namespace.
        """
        if ordering and not (new_child.tag in ordering):
            if (known_namespaces and
                    (XML.get_ns(new_child.tag) in known_namespaces)):
                logger.warning("New child '{0}' is not in the list of "
                               "expected children under '{1}': {2}"
                               .format(new_child.tag,
                                       XML.strip_ns(parent.tag),
                                       ordering))
            # Assume this is some sort of custom element, which
            # implicitly goes at the end of the list.
            ordering = None

        if not ordering:
            parent.append(new_child)
        else:
            new_index = ordering.index(new_child.tag)
            i = 0
            found_position = False
            for child in list(parent):
                try:
                    if ordering.index(child.tag) > new_index:
                        found_position = True
                        break
                except ValueError:
                    if (known_namespaces and (XML.get_ns(child.tag) in
                                              known_namespaces)):
                        logger.warning(
                            "Existing child element '{0}' is not in expected "
                            "list of children under '{1}': \n{2}"
                            .format(child.tag,
                                    XML.strip_ns(parent.tag),
                                    ordering))
                    # Assume this is some sort of custom element - all known
                    # elements should implicitly come before it.
                    found_position = True
                    break
                i += 1
            if found_position:
                parent.insert(i, new_child)
            else:
                parent.append(new_child)

    @classmethod
    def set_or_make_child(cls, parent, tag, text=None, attrib=None,
                          ordering=None, known_namespaces=None):
        """Update or create a child element under the specified parent element.

        :param xml.etree.ElementTree.Element parent: Parent element
        :param str tag: Child element text tag to find or create
        :param str text: Value to set the child's text attribute to
        :param dict attrib: Dict of child attributes to match on
           while searching and set in the final child element
        :param list ordering: See :meth:`add_child`
        :param list known_namespaces: See :meth:`add_child`
        :return: New or updated child Element.
        :rtype: xml.etree.ElementTree.Element
        """
        assert parent is not None
        if attrib is None:
            attrib = {}
        element = cls.find_child(parent, tag, attrib=attrib)
        if element is None:
            logger.debug("Creating new {0} under {1}"
                         .format(XML.strip_ns(tag), XML.strip_ns(parent.tag)))
            element = ET.Element(tag)
            XML.add_child(parent, element, ordering, known_namespaces)
        if text is not None:
            element.text = str(text)
        for a in attrib:
            element.set(a, attrib[a])
        return element
