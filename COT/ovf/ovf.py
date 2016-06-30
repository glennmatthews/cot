#!/usr/bin/env python
#
# ovf.py - Class for OVF/OVA handling
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

# TODO update me
"""Module for handling OVF and OVA virtual machine description files.

**Functions**

.. autosummary::
  :nosignatures:

  byte_count
  byte_string
  factor_bytes

**Classes**

.. autosummary::
  :nosignatures:

  OVF
"""

import logging
import os
import os.path
import re
import tarfile
import xml.etree.ElementTree as ET
# In 2.7+, ET raises a ParseError if XML parsing fails,
# but in 2.6 it raises an ExpatError. Hide this variation.
try:
    from xml.etree.ElementTree import ParseError
except ImportError:
    from xml.parsers.expat import ExpatError as ParseError
import textwrap
from contextlib import closing

from COT.xml_file import XML, register_namespace
from COT.vm_description import VMDescription, VMInitError
from COT.data_validation import match_or_die, check_for_conflict
from COT.data_validation import ValueTooHighError, ValueUnsupportedError
from COT.data_validation import canonicalize_nic_subtype
from COT.file_reference import FileOnDisk, FileInTAR
from COT.helpers import get_checksum, get_disk_capacity, convert_disk_image
from COT.platforms import platform_from_product_class, GenericPlatform

from COT.ovf.name_helper import name_helper
from COT.ovf.hardware import OVFHardware, OVFHardwareDataError
from COT.ovf.item import list_union

logger = logging.getLogger(__name__)


def byte_count(base_val, multiplier):
    """Convert an OVF-style value + multiplier into decimal byte count.

    Inverse operation of :func:`factor_bytes`.

    ::

      >>> byte_count("128", "byte * 2^20")
      134217728
      >>> byte_count("512", "MegaBytes")
      536870912

    :param str base_val: Base value string (value of ``ovf:capacity``, etc.)
    :param str multiplier: Multiplier string (value of
      ``ovf:capacityAllocationUnits``, etc.)

    :return: Number of bytes
    :rtype: int
    """
    if not multiplier:
        return int(base_val)

    # multiplier like 'byte * 2^30'
    match = re.search(r"2\^(\d+)", multiplier)
    if match:
        return int(base_val) << int(match.group(1))

    # multiplier like 'MegaBytes'
    si_prefixes = ["", "kilo", "mega", "giga", "tera"]
    match = re.search("^(.*)bytes$", multiplier, re.IGNORECASE)
    if match:
        shift = si_prefixes.index(match.group(1).lower())
        # Technically the below is correct:
        #   return int(base_val) * (1000 ** shift)
        # but instead we'll reflect common usage:
        return int(base_val) << (10 * shift)

    if multiplier and multiplier != 'byte':
        logger.warning("Unknown multiplier string '%s'", multiplier)

    return int(base_val)


def factor_bytes(byte_value):
    """Convert a byte count into OVF-style bytes + multiplier.

    Inverse operation of :func:`byte_count`

    ::

      >>> factor_bytes(134217728)
      ('128', 'byte * 2^20')
      >>> factor_bytes(134217729)
      ('134217729', 'byte')

    :param int byte_value: Number of bytes
    :return: ``(base_val, multiplier)``
    """
    shift = 0
    byte_value = int(byte_value)
    while byte_value % 1024 == 0:
        shift += 10
        byte_value /= 1024
    byte_str = str(int(byte_value))
    if shift == 0:
        return (byte_str, "byte")
    return (byte_str, "byte * 2^{0}".format(shift))


def byte_string(byte_value, base_shift=0):
    """Pretty-print the given bytes value.

    ::

      >>> byte_string(512)
      '512 B'
      >>> byte_string(512, 2)
      '512 MiB'
      >>> byte_string(65536, 2)
      '64 GiB'
      >>> byte_string(65547)
      '64.01 KiB'
      >>> byte_string(65530, 3)
      '63.99 TiB'
      >>> byte_string(1023850)
      '999.9 KiB'
      >>> byte_string(1024000)
      '1000 KiB'
      >>> byte_string(1048575)
      '1024 KiB'
      >>> byte_string(1049200)
      '1.001 MiB'
      >>> byte_string(2560)
      '2.5 KiB'

    :param float byte_value: Value
    :param int base_shift: Base value of byte_value
      (0 = bytes, 1 = KiB, 2 = MiB, etc.)
    :return: Pretty-printed byte string such as "1.00 GiB"
    """
    tags = ["B", "KiB", "MiB", "GiB", "TiB"]
    byte_value = float(byte_value)
    shift = base_shift
    while byte_value >= 1024.0:
        byte_value /= 1024.0
        shift += 1
    return "{0:.4g} {1}".format(byte_value, tags[shift])


class OVF(VMDescription, XML):
    """Representation of the contents of an OVF or OVA.

    **Properties**

    .. autosummary::
      :nosignatures:

      input_file
      output_file
      ovf_version
      product_class
      platform
      config_profiles
      default_config_profile
      environment_properties
      environment_transports
      networks
      system_types
      version_short
      version_long
    """

    # API methods to be called by clients

    @classmethod
    def detect_type_from_name(cls, filename):
        """Check the given filename to see if it looks like a type we support.

        For our purposes, the file needs to match ".ov[af]" to appear to be
        an OVF/OVA file. We also support names like "foo.ovf.20150101" as those
        have been seen in the wild.

        Does not check file contents, as the given filename may not yet exist.

        :return: '.ovf' or '.ova'
        :raise ValueUnsupportedError: if filename doesn't match ovf/ova
        """
        # We don't care about any directory path
        filename = os.path.basename(filename)
        extension = os.path.splitext(filename)[1]

        if extension == ".ovf" or extension == ".ova":
            return extension
        # Some sources of files are not good about preserving the extension
        # and hence tend to append additional extensions - while this may open
        # us to incorrect behavior (assuming that 'foo.ovf.zip' is a valid OVF
        # when it's probably a zip of an OVF) we'll err on the side of
        # accepting too much rather than incorrectly rejecting something like
        # "foo.ova.2014.05.06A" that's just lazily named.
        m = re.search(r"(\.ov[fa])[^a-zA-Z0-9]", filename)
        if m:
            extension = m.group(1)
            logger.warning("Filename '%s' does not end in '.ovf' or '.ova', "
                           "but found '%s' in mid-filename; treating as such.",
                           filename, extension)
            return extension

        raise ValueUnsupportedError("filename", filename, ('.ovf', '.ova'))

    def _ovf_descriptor_from_name(self, input_file):
        """Get the OVF descriptor for the given file.

        1. The file may be an OVF descriptor itself.
        2. The file may be an OVA, in which case we need to untar it and
           return the path to the extracted OVF descriptor.
        """
        extension = self.detect_type_from_name(input_file)
        if extension == '.ova':
            # Untar the ova to our working directory
            return self.untar(input_file)
        elif extension == '.ovf':
            return input_file
        else:
            return None

    def __init__(self, input_file, output_file):
        """Open the specified OVF and read its XML into memory.

        :param str input_file: Data file to read in.
        :param str output_file: File name to write to. If this VM is read-only,
          (there will never be an output file) this value should be ``None``;
          if the output filename is not yet known, use ``""`` and subsequently
          set :attr:`output_file` when it is determined.
        """
        try:
            self.output_extension = None
            VMDescription.__init__(self, input_file, output_file)

            # Make sure we know how to read the input
            self.ovf_descriptor = self._ovf_descriptor_from_name(input_file)
            if self.ovf_descriptor is None:
                # We should never get here, but be safe...
                raise VMInitError(
                    2,
                    "File {0} does not appear to be an OVA or OVF"
                    .format(input_file))

            # Open the provided OVF
            try:
                XML.__init__(self, self.ovf_descriptor)
            except ParseError as e:
                raise VMInitError(2, "XML parser error in reading {0}: {1}"
                                  .format(self.ovf_descriptor, str(e)))

            # Quick sanity check before we go any further:
            if ((not re.search(r"Envelope", self.root.tag)) or
                    (XML.strip_ns(self.root.tag) != 'Envelope')):
                raise VMInitError(
                    2,
                    "File {0} does not appear to be an OVF descriptor - "
                    "expected top-level element {1} but found {2} "
                    "instead!".format(self.ovf_descriptor, 'Envelope',
                                      self.root.tag))

            self._ovf_version = None
            self.name_helper = name_helper(self.ovf_version)

            for (prefix, URI) in self.NSM.items():
                register_namespace(prefix, URI)

            # Register additional non-standard namespaces we're aware of:
            register_namespace('vmw', "http://www.vmware.com/schema/ovf")
            register_namespace('vbox', "http://www.virtualbox.org/ovf/machine")

            # Go ahead and set pointers to some of the most useful XML sections
            self.envelope = self.root
            self.references = self.find_child(
                self.envelope,
                self.REFERENCES,
                required=True)
            self.disk_section = self.find_child(
                self.envelope,
                self.DISK_SECTION,
                attrib=self.DISK_SECTION_ATTRIB)
            self.network_section = self.find_child(
                self.envelope,
                self.NETWORK_SECTION,
                attrib=self.NETWORK_SECTION_ATTRIB)
            self.deploy_opt_section = self.find_child(
                self.envelope,
                self.DEPLOY_OPT_SECTION,
                required=False)
            self.virtual_system = self.find_child(
                self.envelope,
                self.VIRTUAL_SYSTEM,
                attrib=self.VIRTUAL_SYSTEM_ATTRIB,
                required=True)
            self.product_section = self.find_child(
                self.virtual_system,
                self.PRODUCT_SECTION,
                attrib=self.PRODUCT_SECTION_ATTRIB)
            self.annotation_section = self.find_child(
                self.virtual_system,
                self.ANNOTATION_SECTION,
                attrib=self.ANNOTATION_SECTION_ATTRIB)
            self.virtual_hw_section = self.find_child(
                self.virtual_system,
                self.VIRTUAL_HW_SECTION,
                attrib=self.VIRTUAL_HW_SECTION_ATTRIB,
                required=True)

            # Initialize various caches
            self._configuration_profiles = None
            self._file_references = {}
            self._platform = None

            try:
                self.hardware = OVFHardware(self)
            except OVFHardwareDataError as e:
                raise VMInitError(1,
                                  "OVF descriptor is invalid: {0}".format(e))

            assert self.platform

            self._init_check_file_entries()

        except Exception as e:
            self.destroy()
            raise

    def _init_check_file_entries(self):
        """Check files described in the OVF and store file references."""
        file_list = [f.get(self.FILE_HREF) for f in
                     self.references.findall(self.FILE)]
        if self.input_file == self.ovf_descriptor:
            # Check files in the directory referenced by the OVF descriptor
            input_path = os.path.dirname(self.ovf_descriptor)
            ref_cls = FileOnDisk
        else:
            # OVA - check contents of TAR file.
            input_path = self.input_file
            ref_cls = FileInTAR

        for f in file_list:
            try:
                self._file_references[f] = ref_cls(input_path, f)
            except IOError:
                logger.error("File '%s' referenced in the OVF descriptor "
                             "does not exist.", f)
                self._file_references[f] = None

    @property
    def output_file(self):
        """OVF or OVA file that will be created or updated by :meth:`write`.

        :raise ValueUnsupportedError: if :func:`detect_type_from_name` fails
        """
        return super(OVF, self).output_file

    @output_file.setter
    def output_file(self, output_file):
        # Make sure we can write the requested output format, or abort:
        if output_file:
            self.output_extension = self.detect_type_from_name(output_file)
        super(OVF, self.__class__).output_file.fset(self, output_file)

    @property
    def ovf_version(self):
        """Float representing the OVF specification version in use.

        Supported values at present are 0.9, 1.0, and 2.0.
        """
        if self._ovf_version is None:
            root_namespace = XML.get_ns(self.root.tag)
            logger.verbose("Root namespace is " + root_namespace)
            if root_namespace == 'http://www.vmware.com/schema/ovf/1/envelope':
                logger.info("OVF version is 0.9")
                self._ovf_version = 0.9
            elif root_namespace == 'http://schemas.dmtf.org/ovf/envelope/1':
                logger.info("OVF version is 1.x")
                self._ovf_version = 1.0
            elif root_namespace == 'http://schemas.dmtf.org/ovf/envelope/2':
                logger.info("OVF version is 2.x")
                self._ovf_version = 2.0
            else:
                raise VMInitError(
                    2,
                    "File {0} has an Envelope but it is in "
                    "unknown namespace {1}"
                    .format(self.ovf_descriptor, root_namespace))
        return self._ovf_version

    @property
    def product_class(self):
        """The product class identifier, such as com.cisco.csr1000v."""
        if self._product_class is None and self.product_section is not None:
            self._product_class = self.product_section.get(self.PRODUCT_CLASS)
        return super(OVF, self).product_class

    @product_class.setter
    def product_class(self, product_class):
        if product_class == self.product_class:
            return
        if self.product_section is None:
            self.product_section = self.set_or_make_child(
                self.virtual_system, self.PRODUCT_SECTION,
                attrib=self.PRODUCT_SECTION_ATTRIB)
            # Any Section must have an Info as child
            self.set_or_make_child(self.product_section, self.INFO,
                                   "Product Information")
        if self.product_class:
            logger.info("Changing product class from '%s' to '%s'",
                        self.product_class, product_class)
        self.product_section.set(self.PRODUCT_CLASS, product_class)
        self._product_class = product_class

        # Change platform as well!
        self._platform = None
        assert self.platform

    @property
    def platform(self):
        """The platform type, as determined from the OVF descriptor.

        :type: Class object - :class:`~COT.platforms.GenericPlatform` or
          a more-specific subclass if recognized as such.
        """
        if self._platform is None:
            self._platform = platform_from_product_class(self.product_class)
            logger.info("OVF product class %s --> platform %s",
                        self.product_class, self.platform.__name__)
        return self._platform

    def validate_hardware(self):
        """Check sanity of hardware properties for this VM/product/platform.

        :return: ``True`` if hardware is sane, ``False`` if not.
        """
        result = True

        # TODO refactor to share logic with profile_info_list()
        profile_ids = self.config_profiles
        if not profile_ids:
            profile_ids = [None]

        plat = self.platform

        def _validate_helper(label, fn, *args):
            """Call validation function, catch errors and warn user instead."""
            try:
                fn(*args)
                return True
            except ValueUnsupportedError as e:
                logger.warning(label + str(e))
                return False

        for profile_id in profile_ids:
            profile_str = ""
            if profile_id:
                profile_str = "In profile '{0}':".format(profile_id)
            cpu_item = self.hardware.find_item('cpu', profile=profile_id)
            if cpu_item:
                cpus = cpu_item.get_value(self.VIRTUAL_QUANTITY,
                                          [profile_id])
                result &= _validate_helper(profile_str,
                                           plat.validate_cpu_count, int(cpus))

            ram_item = self.hardware.find_item('memory', profile=profile_id)
            if ram_item:
                megabytes = (byte_count(
                    ram_item.get_value(self.VIRTUAL_QUANTITY, [profile_id]),
                    ram_item.get_value(self.ALLOCATION_UNITS, [profile_id])
                ) / (1024 * 1024))
                result &= _validate_helper(profile_str,
                                           plat.validate_memory_amount,
                                           int(megabytes))

            nics = self.hardware.get_item_count('ethernet', profile_id)
            result &= _validate_helper(profile_str,
                                       plat.validate_nic_count, nics)

            eth_subtypes = list_union(
                *[eth.get_all_values(self.RESOURCE_SUB_TYPE) for
                  eth in self.hardware.find_all_items('ethernet')])
            result &= _validate_helper(profile_str,
                                       plat.validate_nic_types, eth_subtypes)

            # TODO: validate_ide_subtypes
            # TODO: validate_scsi_subtypes

        return result

    @property
    def config_profiles(self):
        """The list of supported configuration profiles.

        If this OVF has no defined profiles, returns an empty list.
        If there is a default profile, it will be first in the list.
        """
        if self._configuration_profiles is None:
            profile_ids = []
            if self.deploy_opt_section is not None:
                profiles = self.deploy_opt_section.findall(self.CONFIG)
                for profile in profiles:
                    # Force the "default" profile to the head of the list
                    if (profile.get(self.CONFIG_DEFAULT) == 'true' or
                            profile.get(self.CONFIG_DEFAULT) == '1'):
                        profile_ids.insert(0, profile.get(self.CONFIG_ID))
                    else:
                        profile_ids.append(profile.get(self.CONFIG_ID))
            logger.verbose("Current configuration profiles are: %s",
                           profile_ids)
            self._configuration_profiles = profile_ids
        return self._configuration_profiles

    @property
    def environment_properties(self):
        """The array of environment properties.

        :return: Array of dicts (one per property) with the keys
          ``"key"``, ``"value"``, ``"qualifiers"``, ``"type"``,
          ``"label"``, and ``"description"``.
        """
        result = []
        if self.ovf_version < 1.0 or self.product_section is None:
            return result
        elems = self.product_section.findall(self.PROPERTY)
        for elem in elems:
            label = elem.findtext(self.PROPERTY_LABEL, "")
            descr = elem.findtext(self.PROPERTY_DESC, "")
            result.append({
                'key': elem.get(self.PROP_KEY),
                'value': elem.get(self.PROP_VALUE),
                'qualifiers': elem.get(self.PROP_QUAL, ""),
                'type': elem.get(self.PROP_TYPE, ""),
                'label': label,
                'description': descr,
            })

        return result

    @property
    def environment_transports(self):
        """The list of environment transport methods.

        :rtype: list[str]
        """
        if self.ovf_version < 1.0:
            return None
        if self.virtual_hw_section is not None:
            value = self.virtual_hw_section.get(self.ENVIRONMENT_TRANSPORT)
            if value:
                return value.split(" ")
        return None

    @environment_transports.setter
    def environment_transports(self, transports):
        if self.ovf_version < 1.0:
            raise NotImplementedError("No support for setting environment"
                                      "transports value on OVF 0.9 format.")
        transports_string = " ".join(transports)
        logger.info("Setting %s to '%s'", self.ENVIRONMENT_TRANSPORT,
                    transports_string)
        self.virtual_hw_section.set(self.ENVIRONMENT_TRANSPORT,
                                    transports_string)

    @property
    def networks(self):
        """The list of network names currently defined in this VM.

        :rtype: list[str]
        """
        if self.network_section is None:
            return []
        return [network.get(self.NETWORK_NAME) for
                network in self.network_section.findall(self.NETWORK)]

    @property
    def system_types(self):
        """List of virtual system type(s) supported by this virtual machine.

        For an OVF, this corresponds to the ``VirtualSystemType`` element.
        """
        if self.virtual_hw_section is not None:
            system = self.virtual_hw_section.find(self.SYSTEM)
            if system is not None:
                value = system.findtext(self.VIRTUAL_SYSTEM_TYPE, None)
                if value:
                    return value.split(" ")
        return None

    @system_types.setter
    def system_types(self, type_list):
        type_string = " ".join(type_list)
        logger.info("Setting VirtualSystemType to '%s'", type_string)
        system = self.virtual_hw_section.find(self.SYSTEM)
        if system is None:
            system = XML.set_or_make_child(self.virtual_hw_section,
                                           self.SYSTEM,
                                           ordering=(self.INFO, self.SYSTEM,
                                                     self.ITEM))
            # A System must have some additional children to be valid:
            XML.set_or_make_child(system, self.VSSD + "ElementName",
                                  "Virtual System Type")
            XML.set_or_make_child(system, self.VSSD + "InstanceID", 0)
        XML.set_or_make_child(system, self.VIRTUAL_SYSTEM_TYPE, type_string)

    @property
    def product(self):
        """Short descriptive product string (XML ``Product`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.PRODUCT, None)
        return None

    @product.setter
    def product(self, product_string):
        logger.info("Updating Product element in OVF")
        self.set_product_section_child(self.PRODUCT, product_string)

    @property
    def vendor(self):
        """Short descriptive vendor string (XML ``Vendor`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.VENDOR, None)
        return None

    @vendor.setter
    def vendor(self, vendor_string):
        logger.info("Updating Vendor element in OVF")
        self.set_product_section_child(self.VENDOR, vendor_string)

    @property
    def version_short(self):
        """Short descriptive version string (XML ``Version`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.VERSION, None)
        return None

    @version_short.setter
    def version_short(self, version_string):
        logger.info("Updating Version element in OVF")
        self.set_product_section_child(self.VERSION, version_string)

    @property
    def version_long(self):
        """Long descriptive version string (XML ``FullVersion`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.FULL_VERSION, None)
        return None

    @version_long.setter
    def version_long(self, version_string):
        logger.info("Updating FullVersion element in OVF")
        self.set_product_section_child(self.FULL_VERSION, version_string)

    @property
    def product_url(self):
        """Product URL string (XML ``ProductUrl`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.PRODUCT_URL, None)
        return None

    @product_url.setter
    def product_url(self, product_url_string):
        logger.info("Updating ProductUrl element in OVF")
        self.set_product_section_child(self.PRODUCT_URL, product_url_string)

    @property
    def vendor_url(self):
        """Vendor URL string (XML ``VendorUrl`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.VENDOR_URL, None)
        return None

    @vendor_url.setter
    def vendor_url(self, vendor_url_string):
        logger.info("Updating VendorUrl element in OVF")
        self.set_product_section_child(self.VENDOR_URL, vendor_url_string)

    @property
    def application_url(self):
        """Application URL string (XML ``AppUrl`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.APPLICATION_URL, None)
        return None

    @application_url.setter
    def application_url(self, app_url_string):
        logger.info("Updating AppUrl element in OVF")
        self.set_product_section_child(self.APPLICATION_URL, app_url_string)

    def __getattr__(self, name):
        """Transparently pass attribute lookups off to name_helper."""
        # Don't pass 'special' attributes through to the helper
        if re.match(r"^__", name):
            raise AttributeError("'OVF' object has no attribute '{0}'"
                                 .format(name))
        return getattr(self.name_helper, name)

    def write(self):
        """Write OVF or OVA to :attr:`output_file`, if set."""
        if not self.output_file:
            return

        prefix = os.path.splitext(self.output_file)[0]
        extension = self.output_extension

        # Update the XML ElementTree to reflect any hardware changes
        self.hardware.update_xml()

        # Validate the hardware to be written
        self.validate_hardware()

        # Make sure file references are correct:
        self.validate_and_update_file_references()

        # Make sure all defined networks are actually used by NICs,
        # and delete any networks that are unused.
        self.validate_and_update_networks()

        logger.info("Writing out to file %s", self.output_file)

        if extension == '.ova':
            ovf_file = os.path.join(self.working_dir, "{0}.ovf"
                                    .format(os.path.basename(prefix)))
            self.write_xml(ovf_file)
            self.generate_manifest(ovf_file)
            self.tar(ovf_file, self.output_file)
        elif extension == '.ovf':
            self.write_xml(self.output_file)
            # Copy all files from working directory to destination
            dest_dir = os.path.dirname(os.path.abspath(self.output_file))
            if not dest_dir:
                dest_dir = os.getcwd()

            for file_obj in self.references.findall(self.FILE):
                file_name = file_obj.get(self.FILE_HREF)
                file_ref = self._file_references[file_name]
                file_ref.copy_to(dest_dir)

            # Generate manifest
            self.generate_manifest(self.output_file)
        else:
            # We should never get here, but to be safe:
            raise NotImplementedError("Not sure how to write a '{0}' file"
                                      .format(extension))

    def validate_and_update_file_references(self):
        """Check all File entries to make sure they are valid and up to date.

        Helper method for :func:`write`.
        """
        for file_elem in self.references.findall(self.FILE):
            href = file_elem.get(self.FILE_HREF)
            file_ref = self._file_references[href]

            if file_ref is not None and not file_ref.exists():
                # file used to exist but no longer does??
                logger.error("Referenced file '%s' does not exist!", href)
                self._file_references[href] = None
                file_ref = None

            if file_ref is None:
                # TODO this should probably have a confirm() check...
                logger.warning("Removing reference to missing file %s", href)
                self.references.remove(file_elem)
                # TODO remove references to this file from Disk, Item?
                continue

            real_size = str(file_ref.size())
            real_capacity = None
            # We can't check disk capacity inside a tar file.
            # It seems wasteful to extract the disk file (could be
            # quite large) from the TAR just to check, so we don't.
            if file_ref.file_path is not None:
                real_capacity = get_disk_capacity(file_ref.file_path)

            disk_item = self.find_disk_from_file_id(
                file_elem.get(self.FILE_ID))

            reported_size = file_elem.get(self.FILE_SIZE)
            if real_size != reported_size:
                # FILE_SIZE is optional in the OVF standard
                if reported_size is not None:
                    logger.warning("Size of file '%s' seems to have changed "
                                   "from %s (reported in the original OVF) "
                                   "to %s (current file size). "
                                   "The updated OVF will reflect this change.",
                                   href, reported_size, real_size)
                file_elem.set(self.FILE_SIZE, real_size)

            if disk_item is not None and real_capacity is not None:
                reported_capacity = str(self.get_capacity_from_disk(disk_item))
                if reported_capacity != real_capacity:
                    logger.warning(
                        "Capacity of disk '%s' seems to have changed "
                        "from %s (reported in the original OVF) "
                        "to %s (actual capacity). "
                        "The updated OVF will reflect this change.",
                        href, reported_capacity, real_capacity)
                    self.set_capacity_of_disk(disk_item, real_capacity)

    def validate_and_update_networks(self):
        """Make sure all defined networks are actually used by NICs.

        Delete any networks that are unused and warn the user.
        Helper method for :func:`write`.
        """
        if self.network_section is None:
            return

        networks = self.network_section.findall(self.NETWORK)
        items = self.virtual_hw_section.findall(self.ETHERNET_PORT_ITEM)
        connected_networks = set()
        for item in items:
            conn = item.find(self.EPASD + self.CONNECTION)
            if conn is not None:
                connected_networks.add(conn.text)
        for net in networks:
            name = net.get(self.NETWORK_NAME)
            if name not in connected_networks:
                logger.warning("Removing unused network %s", name)
                self.network_section.remove(net)
        # If all networks were removed, remove the NetworkSection too
        if not self.network_section.findall(self.NETWORK):
            logger.warning("No networks left - removing NetworkSection")
            self.envelope.remove(self.network_section)
            self.network_section = None

    def _info_string_header(self, width):
        """Generate OVF/OVA file header for :meth:`info_string`."""
        str_list = []
        str_list.append('-' * width)
        str_list.append(self.input_file)
        if self.platform and self.platform is not GenericPlatform:
            str_list.append("COT detected platform type: {0}"
                            .format(self.platform.PLATFORM_NAME))
        str_list.append('-' * width)
        return '\n'.join(str_list)

    def _info_string_product(self, verbosity_option, wrapper):
        """Generate product information as part of :meth:`info_string`."""
        if ((not any([self.product, self.vendor, self.version_short])) and
            (verbosity_option == 'brief' or not any([
                self.product_url, self.vendor_url, self.version_long]))):
            return None
        str_list = []
        wrapper.initial_indent = ''
        wrapper.subsequent_indent = '          '
        # All elements in this section are optional
        for label, value, default, verbose_only in [
                ["Product:  ", self.product, "(No product string)", False],
                ["          ", self.product_url, "(No product URL)", True],
                ["Vendor:   ", self.vendor, "(No vendor string)", False],
                ["          ", self.vendor_url, "(No vendor URL)", True],
                ["Version:  ", self.version_short,
                 "(No version string)", False],
                ["          ", self.version_long,
                 "(No detailed version string)", True],
        ]:
            if verbosity_option == 'brief' and verbose_only:
                continue
            if value is None:
                value = default
            str_list.extend(wrapper.wrap("{0}{1}".format(label, value)))

        return "\n".join(str_list)

    def _info_string_annotation(self, wrapper):
        """Generate annotation information as part of :meth:`info_string`."""
        if self.annotation_section is None:
            return None
        ann = self.annotation_section.find(self.ANNOTATION)
        if ann is None or not ann.text:
            return None
        str_list = []
        first = True
        wrapper.initial_indent = 'Annotation: '
        wrapper.subsequent_indent = '            '
        for line in ann.text.splitlines():
            if not line:
                str_list.append("")
            else:
                str_list.extend(wrapper.wrap(line))
            if first:
                wrapper.initial_indent = wrapper.subsequent_indent
                first = False
        return "\n".join(str_list)

    def _info_string_eula(self, verbosity_option, wrapper):
        """Generate EULA information as part of :meth:`info_string`."""
        # An OVF may have zero, one, or more
        eula_header = False
        str_list = []
        for e in self.find_all_children(self.virtual_system,
                                        self.EULA_SECTION,
                                        self.EULA_SECTION_ATTRIB):
            info = e.find(self.INFO)
            lic = e.find(self.EULA_LICENSE)
            if lic is not None and lic.text:
                if not eula_header:
                    str_list.append("End User License Agreement(s):")
                    eula_header = True
                if info is not None and info.text:
                    wrapper.initial_indent = '  '
                    wrapper.subsequent_indent = '  '
                    str_list.extend(wrapper.wrap(info.text))
                if verbosity_option != 'verbose':
                    str_list.append("    (not displayed, use 'cot info "
                                    "--verbose' if desired)")
                else:
                    wrapper.initial_indent = '    '
                    wrapper.subsequent_indent = '    '
                    for line in lic.text.splitlines():
                        if not line:
                            str_list.append("")
                        else:
                            str_list.extend(wrapper.wrap(line))
        return "\n".join(str_list)

    INFO_STRING_DISK_TEMPLATE = (
        "{{0:{0}}} "  # file/disk name - width is dynamically set
        "{{1:>9}} "   # file size - width 9 for "999.9 MiB"
        "{{2:>9}} "   # disk capacity - width 9 for "999.9 MiB"
        "{{3:.20}}"   # disk info - width 20 for "harddisk @ SCSI 1:15"
    )
    INFO_STRING_DISK_COLUMNS_WIDTH = (1 + 9 + 1 + 9 + 1 + 20)
    INFO_STRING_FILE_TEMPLATE = (
        "{{0:{0}}} "  # file/disk name - width is dynamically set
        "{{1:>9}}"    # file size - width 9 for "999.9 MiB"
    )

    def _info_strings_for_file(self, file_obj):
        """Get attributes of a file which may describe a disk as well.

        Helper for :meth:`_info_string_files_disks`.

        :return: (file_id, file_size, disk_id, disk_capacity, device_info)
        """
        # FILE_SIZE is optional
        reported_size = file_obj.get(self.FILE_SIZE)
        if reported_size is None:
            # TODO - check file size in working dir and/or tarfile
            file_size_str = ""
        else:
            file_size_str = byte_string(file_obj.get(self.FILE_SIZE))

        disk_obj = self.find_disk_from_file_id(file_obj.get(self.FILE_ID))
        if disk_obj is None:
            disk_id = ""
            disk_cap_string = ""
            device_item = self.find_item_from_file(file_obj)
        else:
            disk_id = disk_obj.get(self.DISK_ID)
            disk_cap_string = byte_string(
                self.get_capacity_from_disk(disk_obj))
            device_item = self.find_item_from_disk(disk_obj)
        device_str = self.device_info_str(device_item)

        return (file_obj.get(self.FILE_ID),
                file_size_str,
                disk_id,
                disk_cap_string,
                device_str)

    def _info_string_files_disks(self, width, verbosity_option):
        """Describe files and disks as part of :meth:`info_string`."""
        file_list = self.references.findall(self.FILE)
        disk_list = (self.disk_section.findall(self.DISK)
                     if self.disk_section is not None else [])
        if not (file_list or disk_list):
            return None

        href_w = 0
        if file_list:
            href_w = max([len(f.get(self.FILE_HREF)) for f in file_list])
        href_w = min(href_w, (width - self.INFO_STRING_DISK_COLUMNS_WIDTH - 2))
        href_w = max(href_w, 18)   # len("(placeholder disk)")
        href_w += 2    # leading whitespace for disks
        template = self.INFO_STRING_DISK_TEMPLATE.format(href_w)
        template2 = self.INFO_STRING_FILE_TEMPLATE.format(href_w)

        str_list = [template.format("Files and Disks:",
                                    "File Size", "Capacity", "Device"),
                    template.format("", "---------", "---------",
                                    "--------------------")]
        for file_obj in file_list:
            (file_id, file_size,
             disk_id, disk_cap, device_str) = self._info_strings_for_file(
                 file_obj)

            href_str = "  " + file_obj.get(self.FILE_HREF)
            # Truncate to fit in available space
            if len(href_str) > href_w:
                href_str = href_str[:(href_w-3)] + "..."
            if disk_cap or device_str:
                str_list.append(template.format(href_str, file_size,
                                                disk_cap, device_str))
            else:
                str_list.append(template2.format(href_str, file_size))

            if verbosity_option == 'verbose':
                str_list.append("    File ID: {0}".format(file_id))
                if disk_id:
                    str_list.append("    Disk ID: {0}".format(disk_id))

        # Find placeholder disks as well
        for disk in disk_list:
            file_id = disk.get(self.DISK_FILE_REF)
            file_obj = self.find_child(self.references, self.FILE,
                                       attrib={self.FILE_ID: file_id})
            if file_obj is not None:
                continue   # already reported on above
            disk_cap_string = byte_string(self.get_capacity_from_disk(disk))
            device_item = self.find_item_from_disk(disk)
            device_str = self.device_info_str(device_item)
            str_list.append(template.format("  (disk placeholder)",
                                            "--",
                                            disk_cap_string,
                                            device_str))
        return "\n".join(str_list)

    def _info_string_hardware(self, wrapper):
        """Describe hardware subtypes as part of :meth:`info_string`."""
        virtual_system_types = self.system_types
        scsi_subtypes = list_union(
            *[scsi_ctrl.get_all_values(self.RESOURCE_SUB_TYPE) for
              scsi_ctrl in self.hardware.find_all_items('scsi')])
        ide_subtypes = list_union(
            *[ide_ctrl.get_all_values(self.RESOURCE_SUB_TYPE) for
              ide_ctrl in self.hardware.find_all_items('ide')])
        eth_subtypes = list_union(
            *[eth.get_all_values(self.RESOURCE_SUB_TYPE) for
              eth in self.hardware.find_all_items('ethernet')])

        if ((virtual_system_types is not None) or
                (scsi_subtypes or ide_subtypes or eth_subtypes)):
            str_list = ["Hardware Variants:"]
            wrapper.subsequent_indent = ' ' * 28
            if virtual_system_types is not None:
                wrapper.initial_indent = "  System types:             "
                str_list.extend(wrapper.wrap(" ".join(virtual_system_types)))
            if scsi_subtypes:
                wrapper.initial_indent = "  SCSI device types:        "
                str_list.extend(wrapper.wrap(" ".join(scsi_subtypes)))
            if ide_subtypes:
                wrapper.initial_indent = "  IDE device types:         "
                str_list.extend(wrapper.wrap(" ".join(ide_subtypes)))
            if eth_subtypes:
                wrapper.initial_indent = "  Ethernet device types:    "
                str_list.extend(wrapper.wrap(" ".join(eth_subtypes)))
            return "\n".join(str_list)
        return None

    def _info_string_networks(self, width, verbosity_option, wrapper):
        """Describe virtual networks as part of :meth:`info_string`."""
        if self.network_section is None:
            return None
        str_list = ["Networks:"]
        names = []
        descs = []
        for network in self.network_section.findall(self.NETWORK):
            names.append(network.get(self.NETWORK_NAME))
            descs.append(network.findtext(self.NWK_DESC, None))
        max_n = max([len(name) for name in names])
        max_d = max([len(str(desc)) for desc in descs])
        truncate = (max_n + max_d + 6 >= width and
                    verbosity_option != 'verbose')
        wrapper.initial_indent = "  "
        wrapper.subsequent_indent = ' ' * (5 + max_n)
        if truncate:
            max_d = width - 6 - max_n
        for name, desc in zip(names, descs):
            if not desc:
                str_list.append("  " + name)
            elif truncate and len(desc) > max_d:
                str_list.append('  {name:{w}}  "{tdesc}..."'.format(
                    name=name, w=max_n, tdesc=desc[:max_d-3]))
            else:
                str_list.extend(wrapper.wrap(
                    '{name:{w}}  "{desc}"'.format(name=name, w=max_n,
                                                  desc=desc)))
        return "\n".join(str_list)

    def _info_string_nics(self, verbosity_option, wrapper):
        """Describe NICs as part of :meth:`info_string`."""
        if verbosity_option == 'brief':
            return None
        nics = self.hardware.find_all_items('ethernet')
        if not nics:
            return None
        str_list = ["NICs and Associated Networks:"]
        wrapper.initial_indent = '    '
        wrapper.subsequent_indent = '    '
        max_len = max([len(str(nic.get_value(self.ELEMENT_NAME)))
                       for nic in nics])
        max_len = max(max_len, len("<instance 10>"))
        template = "  {name:{len}} : {nwk}"
        for nic in nics:
            network_name = nic.get_value(self.CONNECTION)
            nic_name = nic.get_value(self.ELEMENT_NAME)
            if nic_name is None:
                nic_name = "<instance {0}>".format(
                    nic.get_value(self.INSTANCE_ID))
            str_list.append(template.format(name=nic_name,
                                            len=max_len,
                                            nwk=network_name))
            if verbosity_option == 'verbose':
                desc = nic.get_value(self.ITEM_DESCRIPTION)
                if desc is None:
                    desc = nic.get_value(self.CAPTION)
                if desc is not None:
                    str_list.extend(wrapper.wrap(desc))
        return "\n".join(str_list)

    def _info_string_environment(self, wrapper):
        """Describe environment for :meth:`info_string`."""
        if not self.environment_transports:
            return None
        str_list = ["Environment:"]
        wrapper.initial_indent = '  '
        wrapper.subsequent_indent = '                   '
        str_list.extend(wrapper.wrap(
            "Transport types: {0}"
            .format(" ".join(self.environment_transports))))
        return "\n".join(str_list)

    def _info_string_properties(self, width, verbosity_option, wrapper):
        """Describe config properties for :meth:`info_string`."""
        properties = self.environment_properties
        if not properties:
            return None
        str_list = ["Properties:"]
        max_key = 2 + max([len(str(ph['key'])) for ph in properties])
        max_label = max([len(str(ph['label'])) for ph in properties])
        max_value = max([len(str(ph['value'])) for ph in properties])
        if all(ph['label'] for ph in properties):
            max_width = max_label
        else:
            max_width = max(max_key, max_label)
        wrapper.initial_indent = '      '
        wrapper.subsequent_indent = '      '
        for ph in properties:
            # If we have a label, and the terminal is wide enough,
            # display "<key> label value", else if no label, display
            # "<key> value", else only display "label value"
            if max_label > 0 and (max_key + max_label + max_value <
                                  width - 8):
                format_str = '  {key:{kw}}  {label:{lw}}  {val}'
                str_list.append(format_str.format(
                    key="<{0}>".format(ph['key']),
                    kw=max_key,
                    label=ph['label'],
                    lw=max_label,
                    val=('"{0}"'.format(ph['value'])
                         if ph['value'] is not None
                         else '--')))
            else:
                str_list.append('  {label:{width}}  {val}'.format(
                    label=(ph['label'] if ph['label']
                           else "<{0}>".format(ph['key'])),
                    width=max_width,
                    val=('"{0}"'.format(ph['value'])
                         if ph['value'] is not None
                         else '--')))
            if verbosity_option == 'verbose':
                for line in ph['description'].splitlines():
                    if not line:
                        str_list.append("")
                    else:
                        str_list.extend(wrapper.wrap(line))
        return "\n".join(str_list)

    def info_string(self, width=79, verbosity_option=None):
        """Get a descriptive string summarizing the contents of this OVF.

        :param int width: Line length to wrap to where possible.
        :param str verbosity_option: ``'brief'``, ``None`` (default),
          or ``'verbose'``

        :return: Wrapped, appropriately verbose string.
        """
        # Supposedly it's quicker to construct a list of strings then merge
        # them all together with 'join()' rather than it is to repeatedly
        # append to an existing string with '+'.
        # I haven't profiled this to verify - it's fast enough for now.
        wrapper = textwrap.TextWrapper(width=width)

        # File description
        header = self._info_string_header(width)

        section_list = [
            self._info_string_product(verbosity_option, wrapper),
            self._info_string_annotation(wrapper),
            self._info_string_eula(verbosity_option, wrapper),
            self._info_string_files_disks(width, verbosity_option),
            self._info_string_hardware(wrapper),
            self.profile_info_string(width, verbosity_option),
            self._info_string_networks(width, verbosity_option, wrapper),
            self._info_string_nics(verbosity_option, wrapper),
            self._info_string_environment(wrapper),
            self._info_string_properties(width, verbosity_option, wrapper)
        ]
        # Discard empty sections
        section_list = [s for s in section_list if s]

        return header + '\n' + "\n\n".join(section_list)

    def device_info_str(self, device_item):
        """Get a one-line summary of a hardware device.

        :param OVFItem device_item: Device to summarize
        :return: Descriptive string such as "harddisk @ IDE 1:0"
        """
        if device_item is None:
            return ""
        controller_item = self.find_parent_from_item(device_item)
        if controller_item is None:
            ctrl_type = "(?)"
            ctrl_addr = "?"
        else:
            ctrl_type = self.get_type_from_device(
                controller_item).upper()
            ctrl_addr = controller_item.get_value(self.ADDRESS)
        return "{0} @ {1} {2}:{3}".format(
            self.get_type_from_device(device_item),
            ctrl_type,
            ctrl_addr,
            device_item.get_value(self.ADDRESS_ON_PARENT))

    PROFILE_INFO_TEMPLATE = (
        "{{0:{0}}} "  # profile name - width is dynamically set
        "{{1:>4}} "   # CPUs   - width 4 for "CPUs"
        "{{2:>9}} "   # memory - width 9 for "999.9 MiB"
        "{{3:>4}} "   # NICs   - width 4 for "NICs"
        "{{4:>7}} "   # serial - width 7 for "Serials"
        "{{5:>14}}"   # disks  - width 14 for "Disks/Capacity","10 / 999.9 MiB"
    )

    def profile_info_list(self, width=79, verbose=False):
        """Get a list describing available configuration profiles.

        :param int width: Line length to wrap to if possible
        :param str verbose: if True, generate multiple lines per profile
        :return: (header, list)
        """
        str_list = []

        default_profile_id = self.default_config_profile
        profile_ids = self.config_profiles
        if not profile_ids:
            profile_ids = [None]

        prof_w = max(len("Configuration Profiles: "),
                     2 + max([(len(str(pid))) for pid in profile_ids]),
                     2 + len(str(default_profile_id) + " (default)"))

        # Profile information
        template = self.PROFILE_INFO_TEMPLATE.format(prof_w)
        header = template.format("Configuration Profiles:", "CPUs", "Memory",
                                 "NICs", "Serials", "Disks/Capacity")
        header += "\n" + template.format("", "----", "---------", "----",
                                         "-------", "--------------")
        if verbose:
            wrapper = textwrap.TextWrapper(width=width,
                                           initial_indent='    ',
                                           subsequent_indent=' ' * 21)
        index = 0
        for profile_id in profile_ids:
            cpus = 0
            cpu_item = self.hardware.find_item('cpu', profile=profile_id)
            if cpu_item:
                cpus = cpu_item.get_value(self.VIRTUAL_QUANTITY,
                                          [profile_id])
            mem_bytes = 0
            ram_item = self.hardware.find_item('memory', profile=profile_id)
            if ram_item:
                mem_bytes = byte_count(
                    ram_item.get_value(self.VIRTUAL_QUANTITY, [profile_id]),
                    ram_item.get_value(self.ALLOCATION_UNITS, [profile_id]))
            nics = self.hardware.get_item_count('ethernet', profile_id)
            serials = self.hardware.get_item_count('serial', profile_id)
            disk_count = self.hardware.get_item_count('harddisk',
                                                      profile_id)
            disks_size = 0
            if self.disk_section is not None:
                for disk in self.disk_section.findall(self.DISK):
                    disks_size += self.get_capacity_from_disk(disk)

            profile_str = "  " + str(profile_id)
            if profile_id == default_profile_id:
                profile_str += " (default)"
            str_list.append(template.format(
                profile_str,
                cpus,
                byte_string(mem_bytes),
                nics,
                serials,
                "{0:2} / {1:>9}".format(disk_count,
                                        byte_string(disks_size))))
            if profile_id is not None and verbose:
                profile = self.find_child(self.deploy_opt_section,
                                          self.CONFIG,
                                          attrib={self.CONFIG_ID: profile_id})
                str_list.extend(wrapper.wrap(
                    '{0:15} "{1}"'.format("Label:",
                                          profile.findtext(self.CFG_LABEL))))
                str_list.extend(wrapper.wrap(
                    '{0:15} "{1}"'.format("Description:",
                                          profile.findtext(self.CFG_DESC))))
            index += 1
        return (header, str_list)

    def profile_info_string(self, width=79, verbosity_option=None):
        """Get a string summarizing available configuration profiles.

        :param int width: Line length to wrap to if possible
        :param str verbosity_option: ``'brief'``, ``None`` (default),
          or ``'verbose'``

        :return: Appropriately formatted and verbose string.
        """
        header, str_list = self.profile_info_list(
            width, (verbosity_option != 'brief'))
        return "\n".join([header] + str_list)

    def create_configuration_profile(self, pid, label, description):
        """Create or update a configuration profile with the given ID.

        :param str pid: Profile identifier
        :param str label: Brief descriptive label for the profile
        :param str description: Verbose description of the profile
        """
        self.deploy_opt_section = self.create_envelope_section_if_absent(
            self.DEPLOY_OPT_SECTION, "Configuration Profiles")

        cfg = self.find_child(self.deploy_opt_section, self.CONFIG,
                              attrib={self.CONFIG_ID: pid})
        if cfg is None:
            logger.debug("Creating new Configuration element")
            cfg = ET.SubElement(self.deploy_opt_section, self.CONFIG,
                                {self.CONFIG_ID: pid})

        self.set_or_make_child(cfg, self.CFG_LABEL, label)
        self.set_or_make_child(cfg, self.CFG_DESC, description)
        # Clear cache
        logger.debug("New profile %s created - clear config_profiles cache",
                     pid)
        self._configuration_profiles = None

    def delete_configuration_profile(self, profile):
        """Delete the profile with the given ID."""
        cfg = self.find_child(self.deploy_opt_section, self.CONFIG,
                              attrib={self.CONFIG_ID: profile})
        if cfg is None:
            raise LookupError("No such configuration profile '{0}'"
                              .format(profile))
        logger.info("Deleting configuration profile %s", profile)

        # Delete references to this profile from the hardware
        items = self.hardware.find_all_items(profile_list=[profile])
        logger.verbose("Removing profile %s from %s hardware items",
                       profile, len(items))
        for item in items:
            item.remove_profile(profile, split_default=False)

        # Delete the profile declaration itself
        self.deploy_opt_section.remove(cfg)

        if not self.deploy_opt_section.findall(self.CONFIG):
            self.envelope.remove(self.deploy_opt_section)

        # Clear cache
        logger.debug("Profile %s deleted - clear config_profiles cache",
                     profile)
        self._configuration_profiles = None

    # TODO - how to insert a doc about the profile_list (see vm_description.py)

    def set_cpu_count(self, cpus, profile_list):
        """Set the number of CPUs.

        :param int cpus: Number of CPUs
        :param list profile_list: Change only the given profiles
        """
        logger.info("Updating CPU count in OVF under profile %s to %s",
                    profile_list, cpus)
        self.platform.validate_cpu_count(cpus)
        self.hardware.set_value_for_all_items('cpu',
                                              self.VIRTUAL_QUANTITY, cpus,
                                              profile_list,
                                              create_new=True)

    def set_memory(self, megabytes, profile_list):
        """Set the amount of RAM, in megabytes.

        :param int megabytes: Memory value, in megabytes
        :param list profile_list: Change only the given profiles
        """
        logger.info("Updating RAM in OVF under profile %s to %s",
                    profile_list, megabytes)
        self.platform.validate_memory_amount(megabytes)
        self.hardware.set_value_for_all_items('memory',
                                              self.VIRTUAL_QUANTITY, megabytes,
                                              profile_list,
                                              create_new=True)
        self.hardware.set_value_for_all_items('memory',
                                              self.ALLOCATION_UNITS,
                                              'byte * 2^20',
                                              profile_list)

    def set_nic_types(self, type_list, profile_list):
        """Set the hardware type(s) for NICs.

        :param list type_list: NIC hardware type(s)
        :param list profile_list: Change only the given profiles.
        """
        # Just to be safe...
        type_list = [canonicalize_nic_subtype(t) for t in type_list]
        self.platform.validate_nic_types(type_list)
        self.hardware.set_value_for_all_items('ethernet',
                                              self.RESOURCE_SUB_TYPE,
                                              type_list,
                                              profile_list)

    def get_nic_count(self, profile_list):
        """Get the number of NICs under the given profile(s).

        :param list profile_list: Profile(s) of interest.
        :rtype: dict
        :return: ``{ profile_name : nic_count }``
        """
        return self.hardware.get_item_count_per_profile('ethernet',
                                                        profile_list)

    def set_nic_count(self, count, profile_list):
        """Set the given profile(s) to have the given number of NICs.

        :param int count: number of NICs
        :param list profile_list: Change only the given profiles
        """
        logger.info("Updating NIC count in OVF under profile %s to %s",
                    profile_list, count)
        self.platform.validate_nic_count(count)
        self.hardware.set_item_count_per_profile('ethernet', count,
                                                 profile_list)

    def create_network(self, label, description):
        """Define a new network with the given label and description.

        Also serves to update the description of an existing network label.

        :param str label: Brief label for the network
        :param str description: Verbose description of the network
        """
        self.network_section = self.create_envelope_section_if_absent(
            self.NETWORK_SECTION,
            "Logical networks",
            attrib=self.NETWORK_SECTION_ATTRIB)
        network = self.set_or_make_child(self.network_section, self.NETWORK,
                                         attrib={self.NETWORK_NAME: label})
        self.set_or_make_child(network, self.NWK_DESC, description)

    def set_nic_networks(self, network_list, profile_list):
        """Set the NIC to network mapping for NICs under the given profile(s).

        .. note::
          If the length of :attr:`network_list` is less than the number of
          NICs, will use the last entry in the list for all remaining NICs.

        :param list network_list: List of networks to map NICs to
        :param list profile_list: Change only the given profiles
        """
        self.hardware.set_item_values_per_profile('ethernet',
                                                  self.CONNECTION,
                                                  network_list,
                                                  profile_list,
                                                  default=network_list[-1])

    def set_nic_mac_addresses(self, mac_list, profile_list):
        """Set the MAC addresses for NICs under the given profile(s).

        .. note::
          If the length of :attr:`mac_list` is less than the number of NICs,
          will use the last entry in the list for all remaining NICs.

        :param list mac_list: List of MAC addresses to assign to NICs
        :param list profile_list: Change only the given profiles
        """
        self.hardware.set_item_values_per_profile('ethernet',
                                                  self.ADDRESS,
                                                  mac_list,
                                                  profile_list,
                                                  default=mac_list[-1])

    def set_nic_names(self, name_list, profile_list):
        """Set the device names for NICs under the given profile(s).

        :param list name_list: List of names to assign.
        :param list profile_list: Change only the given profiles
        """
        self.hardware.set_item_values_per_profile('ethernet',
                                                  self.ELEMENT_NAME,
                                                  name_list,
                                                  profile_list)

    def get_serial_count(self, profile_list):
        """Get the number of serial ports under the given profile(s).

        :rtype: dict
        :return: ``{ profile_name : serial_count }``
        """
        return self.hardware.get_item_count_per_profile('serial', profile_list)

    def set_serial_count(self, count, profile_list):
        """Set the given profile(s) to have the given number of serial ports.

        :param int count: Number of serial ports
        :param list profile_list: Change only the given profiles
        """
        logger.info("Updating serial port count under profile %s to %s",
                    profile_list, count)
        self.hardware.set_item_count_per_profile('serial', count, profile_list)

    def set_serial_connectivity(self, conn_list, profile_list):
        """Set the serial port connectivity under the given profile(s).

        :param list conn_list: List of connectivity strings
        :param list profile_list: Change only the given profiles
        """
        self.hardware.set_item_values_per_profile('serial',
                                                  self.ADDRESS, conn_list,
                                                  profile_list, default="")

    def get_serial_connectivity(self, profile):
        """Get the serial port connectivity strings under the given profile.

        :param str profile: Profile of interest.
        :return: List of connectivity strings
        """
        return [item.get_value(self.ADDRESS) for item in
                self.hardware.find_all_items('serial', profile_list=[profile])]

    def set_scsi_subtypes(self, type_list, profile_list):
        """Set the device subtype(s) for the SCSI controller(s).

        :param list type_list: SCSI subtype string list
        :param list profile_list: Change only the given profiles
        """
        # TODO validate supported types by platform
        self.hardware.set_value_for_all_items('scsi',
                                              self.RESOURCE_SUB_TYPE,
                                              type_list,
                                              profile_list)

    def set_ide_subtypes(self, type_list, profile_list):
        """Set the device subtype(s) for the IDE controller(s).

        :param list type_list: IDE subtype string list
        :param list profile_list: Change only the given profiles
        """
        # TODO validate supported types by platform
        self.hardware.set_value_for_all_items('ide',
                                              self.RESOURCE_SUB_TYPE,
                                              type_list,
                                              profile_list)

    def get_property_value(self, key):
        """Get the value of the given property.

        :param str key: Property identifier
        :return: Value of this property, or ``None``
        """
        if self.ovf_version < 1.0 or self.product_section is None:
            return None
        prop = self.find_child(self.product_section, self.PROPERTY,
                               attrib={self.PROP_KEY: key})
        if prop is None:
            return None
        return prop.get(self.PROP_VALUE)

    def _validate_value_for_property(self, prop, value):
        """Check whether the proposed value is valid for the given property.

        This applies agnostic criteria such as property type and qualifiers;
        it knows nothing of the property's actual meaning.

        :param prop: Existing Property element.
        :param str value: Proposed value to set for this property.
        :raise ValueUnsupportedError: if the value does not meet criteria.
        :return: the value, potentially canonicalized.
        """
        key = prop.get(self.PROP_KEY)

        # Check type validity and canonicalize if needed
        prop_type = prop.get(self.PROP_TYPE, "")
        if prop_type == "boolean":
            # XML prefers to represent booleans as 'true' or 'false'
            value = str(value).lower()
            if str(value).lower() in ['true', '1', 't', 'y', 'yes']:
                value = 'true'
            elif str(value).lower() in ['false', '0', 'f', 'n', 'no']:
                value = 'false'
            else:
                raise ValueUnsupportedError(key, value, "a boolean value")
        elif prop_type == "string":
            value = str(value)

        # Check property qualifiers
        prop_qual = prop.get(self.PROP_QUAL, "")
        if prop_qual:
            m = re.search(r"MaxLen\((\d+)\)", prop_qual)
            if m:
                max_len = int(m.group(1))
                if len(value) > max_len:
                    raise ValueUnsupportedError(
                        key, value, "string no longer than {0} characters"
                        .format(max_len))
            m = re.search(r"MinLen\((\d+)\)", prop_qual)
            if m:
                min_len = int(m.group(1))
                if len(value) < min_len:
                    raise ValueUnsupportedError(
                        key, value, "string no shorter than {0} characters"
                        .format(min_len))

        return value

    def set_property_value(self, key, value):
        """Set the value of the given property (converting value if needed).

        :param str key: Property identifier
        :param str value: Value to set for this property
        :return: the (converted) value that was set.
        """
        if self.ovf_version < 1.0:
            raise NotImplementedError("No support for setting environment "
                                      "properties under OVF v0.9")
        if self.product_section is None:
            self.product_section = self.set_or_make_child(
                self.virtual_system, self.PRODUCT_SECTION,
                attrib=self.PRODUCT_SECTION_ATTRIB)
            # Any Section must have an Info as child
            self.set_or_make_child(self.product_section, self.INFO,
                                   "Product Information")
        prop = self.find_child(self.product_section, self.PROPERTY,
                               attrib={self.PROP_KEY: key})
        if prop is None:
            self.set_or_make_child(self.product_section, self.PROPERTY,
                                   attrib={self.PROP_KEY: key,
                                           self.PROP_VALUE: value,
                                           self.PROP_TYPE: 'string'})
            return value

        # Else, make sure the requested value is valid
        value = self._validate_value_for_property(prop, value)

        prop.set(self.PROP_VALUE, value)
        return value

    def config_file_to_properties(self, file_path):
        """Import each line of a text file into a configuration property.

        :raise NotImplementedError: if the :attr:`platform` for this OVF
          does not define
          :const:`~COT.platforms.GenericPlatform.LITERAL_CLI_STRING`
        :param str file_path: File name to import.
        """
        i = 0
        if not self.platform.LITERAL_CLI_STRING:
            raise NotImplementedError("no known support for literal CLI on " +
                                      self.platform.PLATFORM_NAME)
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip blank lines and comment lines
                if (not line) or line[0] == '!':
                    continue
                i += 1
                self.set_property_value(
                    "{0}-{1:04d}".format(self.platform.LITERAL_CLI_STRING, i),
                    line)

    def convert_disk_if_needed(self, file_path, kind):
        """Convert the disk to a more appropriate format if needed.

        * All hard disk files are converted to stream-optimized VMDK as it
          is the only format that VMware supports in OVA packages.
        * CD-ROM iso images are accepted without change.

        :param str file_path: Image to inspect and possibly convert
        :param str kind: Image type (harddisk/cdrom)
        :return:
          * :attr:`file_path`, if no conversion was required
          * or a file path in :attr:`output_dir` containing the converted image
        """
        if kind != 'harddisk':
            logger.debug("No disk conversion needed")
            return file_path

        # Convert hard disk to VMDK format, streamOptimized subformat
        return convert_disk_image(file_path, self.working_dir,
                                  'vmdk', 'streamOptimized')

    def search_from_filename(self, filename):
        """From the given filename, try to find any existing objects.

        This implementation uses the given :attr:`filename` to find a matching
        ``File`` in the OVF, then using that to find a matching ``Disk`` and
        ``Item`` entries.

        :param str filename: Filename to search from
        :return: ``(file, disk, ctrl_item, disk_item)``, any or all of which
          may be ``None``
        """
        file_obj = None
        disk = None
        ctrl_item = None
        disk_item = None

        logger.verbose("Looking for existing disk info based on filename %s",
                       filename)

        file_obj = self.find_child(self.references, self.FILE,
                                   attrib={self.FILE_HREF: filename})

        if file_obj is None:
            return (file_obj, disk, ctrl_item, disk_item)

        file_id = file_obj.get(self.FILE_ID)
        disk = self.find_disk_from_file_id(file_id)

        disk_item_1 = self.find_item_from_file(file_obj)
        disk_item_2 = self.find_item_from_disk(disk)
        disk_item = check_for_conflict("disk Item", [disk_item_1, disk_item_2])

        ctrl_item = self.find_parent_from_item(disk_item)

        if disk_item is not None and ctrl_item is None:
            raise LookupError("Found disk Item {0} but no controller Item "
                              "as its parent?"
                              .format(disk_item))

        return (file_obj, disk, ctrl_item, disk_item)

    def search_from_file_id(self, file_id):
        """From the given file ID, try to find any existing objects.

        This implementation uses the given :attr:`file_id` to find a matching
        ``File`` in the OVF, then using that to find a matching ``Disk`` and
        ``Item`` entries.

        :param str file_id: Filename to search from
        :return: ``(file, disk, ctrl_item, disk_item)``, any or all of which
          may be ``None``
        """
        if file_id is None:
            return (None, None, None, None)

        logger.verbose(
            "Looking for existing disk information based on file_id %s",
            file_id)

        file_obj = None
        disk = None
        ctrl_item = None
        disk_item = None

        file_obj = self.find_child(self.references, self.FILE,
                                   attrib={self.FILE_ID: file_id})

        disk = self.find_disk_from_file_id(file_id)

        if disk is not None and file_obj is None:
            # Should never happen - OVF is not valid
            raise LookupError("Malformed OVF? Found Disk with fileRef {0} but "
                              "no corresponding File with id {0}"
                              .format(file_id))

        disk_item_1 = self.find_item_from_file(file_obj)
        disk_item_2 = self.find_item_from_disk(disk)
        disk_item = check_for_conflict("disk Item", [disk_item_1, disk_item_2])

        ctrl_item = self.find_parent_from_item(disk_item)

        if disk_item is not None and ctrl_item is None:
            raise LookupError("Found disk Item {0} but no controller Item "
                              "as its parent?"
                              .format(disk_item))

        return (file_obj, disk, ctrl_item, disk_item)

    def search_from_controller(self, controller, address):
        """From the controller type and device address, look for existing disk.

        This implementation uses the parameters to find matching
        controller and disk ``Item`` elements, then using the disk ``Item``
        to find matching ``File`` and/or ``Disk``.

        :param str controller: ``'ide'`` or ``'scsi'``
        :param str address: Device address such as ``'1:0'``
        :return: ``(file, disk, ctrl_item, disk_item)``, any or all of which
          may be ``None``
        """
        if controller is None or address is None:
            return (None, None, None, None)

        logger.verbose("Looking for existing disk information based on "
                       "controller type (%s) and disk address (%s)",
                       controller, address)

        file_obj = None
        disk = None
        ctrl_item = None
        disk_item = None

        ctrl_addr = address.split(":")[0]
        disk_addr = address.split(":")[1]
        logger.debug("Searching for controller address %s", ctrl_addr)

        ctrl_item = self.hardware.find_item(controller,
                                            {self.ADDRESS: ctrl_addr})

        if ctrl_item is None:
            return (file_obj, disk, ctrl_item, disk_item)

        # From controller Item to its child disk Item
        ctrl_instance = ctrl_item.get_value(self.INSTANCE_ID)
        logger.debug("Searching for disk address %s with parent %s",
                     disk_addr, ctrl_instance)
        disk_item = self.hardware.find_item(
            properties={self.PARENT: ctrl_instance,
                        self.ADDRESS_ON_PARENT: disk_addr})

        if disk_item is None:
            return (file_obj, disk, ctrl_item, disk_item)

        host_resource = disk_item.get_value(self.HOST_RESOURCE)
        if host_resource is None:
            logger.debug("Disk item has no RASD:HostResource - "
                         "i.e., empty drive")
            return (file_obj, disk, ctrl_item, disk_item)

        if (host_resource.startswith(self.HOST_RSRC_DISK_REF) or
                host_resource.startswith(self.OLD_HOST_RSRC_DISK_REF)):
            logger.debug("Looking for Disk and File matching disk Item")
            # From disk Item to Disk
            disk_id = os.path.basename(host_resource)
            if self.disk_section is not None:
                disk = self.find_child(self.disk_section, self.DISK,
                                       attrib={self.DISK_ID: disk_id})

            if disk is not None:
                # From Disk to File
                file_id = disk.get(self.DISK_FILE_REF)
                file_obj = self.find_child(self.references, self.FILE,
                                           attrib={self.FILE_ID: file_id})
        elif (host_resource.startswith(self.HOST_RSRC_FILE_REF) or
              host_resource.startswith(self.OLD_HOST_RSRC_FILE_REF)):
            logger.debug("Looking for File and Disk matching disk Item")
            # From disk Item to File
            file_id = os.path.basename(host_resource)
            file_obj = self.find_child(self.references, self.FILE,
                                       attrib={self.FILE_ID: file_id})

            if self.disk_section is not None:
                disk = self.find_child(self.disk_section, self.DISK,
                                       attrib={self.DISK_FILE_REF: file_id})
        else:
            logger.warning(
                "Unrecognized HostResource format '%s'; unable to identify "
                "which File and Disk are associated with this disk Item",
                host_resource)

        return (file_obj, disk, ctrl_item, disk_item)

    def find_open_controller(self, controller_type):
        """Find the first open slot on a controller of the given type.

        :param str controller_type: ``'ide'`` or ``'scsi'``
        :return: ``(ctrl_item, address_string)`` or ``(None, None)``
        """
        for ctrl_item in self.hardware.find_all_items(controller_type):
            ctrl_instance = ctrl_item.get_value(self.INSTANCE_ID)
            ctrl_addr = ctrl_item.get_value(self.ADDRESS)
            logger.debug("Found controller instance %s address %s",
                         ctrl_instance, ctrl_addr)
            disk_list = self.hardware.find_all_items(
                properties={self.PARENT: ctrl_instance})
            address_list = [disk.get_value(self.ADDRESS_ON_PARENT) for
                            disk in disk_list]
            disk_addr = 0
            while str(disk_addr) in address_list:
                disk_addr += 1
            if ((controller_type == 'scsi' and disk_addr > 7) or
                    (controller_type == 'ide' and disk_addr > 1)):
                logger.info("Controller address %s is already full", ctrl_addr)
            else:
                logger.info("Found open slot %s:%s", ctrl_addr, disk_addr)
                return (ctrl_item, "{0}:{1}".format(ctrl_addr, disk_addr))

        logger.info("No open controller found")
        return (None, None)

    def get_id_from_file(self, file_obj):
        """Get the file ID from the given opaque file object.

        :param xml.etree.ElementTree.Element file_obj: 'File' element
        :return: 'id' attribute value of this element
        """
        return file_obj.get(self.FILE_ID)

    def get_path_from_file(self, file_obj):
        """Get the file path from the given opaque file object.

        :param xml.etree.ElementTree.Element file_obj: 'File' element
        :return: 'href' attribute value of this element
        """
        return file_obj.get(self.FILE_HREF)

    def get_file_ref_from_disk(self, disk):
        """Get the file reference from the given opaque disk object.

        :param xml.etree.ElementTree.Element disk: 'Disk' element
        :return: 'fileRef' attribute value of this element
        """
        return disk.get(self.DISK_FILE_REF)

    def get_type_from_device(self, device):
        """Get the type of the given device.

        :param OVFItem device: Device object to query
        :return: string such as 'ide' or 'memory'
        """
        device_type = device.get_value(self.RESOURCE_TYPE)
        for key in self.RES_MAP.keys():
            if device_type == self.RES_MAP[key]:
                return key
        return "unknown ({0})".format(device_type)

    def get_subtype_from_device(self, device):
        """Get the sub-type of the given opaque device object.

        :param OVFItem device: Device object to query
        :return: ``None``, or string such as 'virtio' or 'lsilogic', or
          list of strings
        """
        return device.get_value(self.RESOURCE_SUB_TYPE)

    def get_common_subtype(self, device_type):
        """Get the sub-type common to all devices of the given type.

        :param str device_type: Device type such as ``'ide'`` or ``'memory'``.
        :return: ``None``, if multiple such devices exist and they do not all
          have the same sub-type.
        :return: Subtype string common to all devices of the type.
        """
        subtype = None
        for item in self.hardware.find_all_items(device_type):
            item_subtype = item.get_value(self.RESOURCE_SUB_TYPE)
            if subtype is None:
                subtype = item_subtype
                logger.info("Found %s subtype %s", device_type, subtype)
            elif subtype != item_subtype:
                logger.warning("Found different subtypes ('%s', '%s') for "
                               "device type %s - no common subtype exists",
                               subtype, item_subtype, device_type)
                return None
        return subtype

    def check_sanity_of_disk_device(self, disk, file_obj,
                                    disk_item, ctrl_item):
        """Check if the given disk is linked properly to the other objects.

        :param disk: Disk object to validate
        :type disk: xml.etree.ElementTree.Element
        :param file_obj: File object which this disk should be linked to
          (optional)
        :type file_obj: xml.etree.ElementTree.Element
        :param OVFItem disk_item: Disk device object which should link to
          this disk (optional)
        :param OVFItem ctrl_item: Controller device object which should link
          to the :attr:`disk_item`
        :raise ValueMismatchError: if the given items are not linked properly.
        :raise ValueUnsupportedError: if the :attr:`disk_item` has a
          ``HostResource`` value in an unrecognized or invalid format.
        """
        if disk_item is None:
            return
        if ctrl_item is not None:
            match_or_die("disk Item Parent", disk_item.get_value(self.PARENT),
                         "controller Item InstanceID",
                         ctrl_item.get_value(self.INSTANCE_ID))
        host_resource = disk_item.get_value(self.HOST_RESOURCE)
        if host_resource is not None:
            if ((host_resource.startswith(self.HOST_RSRC_DISK_REF) or
                 host_resource.startswith(self.OLD_HOST_RSRC_DISK_REF)) and
                    disk is not None):
                match_or_die("disk Item HostResource",
                             os.path.basename(host_resource),
                             "Disk diskId", disk.get(self.DISK_ID))
            elif ((host_resource.startswith(self.HOST_RSRC_FILE_REF) or
                   host_resource.startswith(self.OLD_HOST_RSRC_FILE_REF)) and
                  file_obj is not None):
                match_or_die("disk Item HostResource",
                             os.path.basename(host_resource),
                             "File id", file_obj.get(self.FILE_ID))
            else:
                raise ValueUnsupportedError("HostResource prefix",
                                            host_resource,
                                            [self.HOST_RSRC_FILE_REF,
                                             self.HOST_RSRC_DISK_REF,
                                             self.OLD_HOST_RSRC_FILE_REF,
                                             self.OLD_HOST_RSRC_DISK_REF])

    def add_file(self, file_path, file_id, file_obj=None, disk=None):
        """Add a new file object to the VM or overwrite the provided one.

        :param str file_path: Path to file to add
        :param str file_id: Identifier string for the file in the VM
        :param file_obj: Existing file object to overwrite
        :type file_obj: xml.etree.ElementTree.Element
        :param disk: Existing disk object referencing :attr:`file`.
        :type disk: xml.etree.ElementTree.Element

        :return: New or updated file object
        """
        logger.debug("Adding File to OVF")

        if file_obj is not None:
            file_obj.clear()
        elif disk is None:
            file_obj = ET.SubElement(self.references, self.FILE)
        else:
            # The OVF standard requires that Disks which reference a File
            # be listed in the same order as the Files.
            # Since there's already a Disk, make sure the new File is ordered
            # appropriately.
            # This is complicated by the fact that we may have
            # Files which are not Disks and Disks with no backing File.
            all_files = self.references.findall(self.FILE)
            all_disks = self.disk_section.findall(self.DISK)

            # Starting from the Disk entry corresponding to our new File,
            # search forward until we find the next Disk (if any) which has a
            # File, and insert our new File before that File.
            disk_index = all_disks.index(disk)
            file_index = len(all_files)
            while disk_index < len(all_disks):
                tmp_file_id = all_disks[disk_index].get(self.DISK_FILE_REF)
                next_file = self.find_child(self.references, self.FILE,
                                            attrib={self.FILE_ID: tmp_file_id})
                if next_file is not None:
                    file_index = all_files.index(next_file)
                    break
                disk_index += 1

            file_obj = ET.Element(self.FILE)
            self.references.insert(file_index, file_obj)

        file_size_string = str(os.path.getsize(file_path))
        file_name = os.path.basename(file_path)

        file_obj.set(self.FILE_ID, file_id)
        file_obj.set(self.FILE_HREF, file_name)
        file_obj.set(self.FILE_SIZE, file_size_string)

        # Make a note of the file's location - we'll copy it at write time.
        self._file_references[file_name] = FileOnDisk(file_path)

        return file_obj

    def remove_file(self, file_obj, disk=None, disk_drive=None):
        """Remove the given file object from the VM.

        :param file_obj: File object to remove
        :type file_obj: xml.etree.ElementTree.Element
        :param disk: Disk object referencing :attr:`file`
        :type disk: xml.etree.ElementTree.Element
        :param OVFItem disk_drive: Disk drive mapping :attr:`file` to a device
        """
        self.references.remove(file_obj)
        del self._file_references[file_obj.get(self.FILE_HREF)]

        if disk is not None:
            self.disk_section.remove(disk)

        if disk_drive is not None:
            # For a CD-ROM drive, we can simply unmap the file.
            # For a hard disk, we need to delete the device altogether.
            drive_type = disk_drive.get_value(self.RESOURCE_TYPE)
            if drive_type == self.RES_MAP['cdrom']:
                disk_drive.set_property(self.HOST_RESOURCE, '')
            elif drive_type == self.RES_MAP['harddisk']:
                self.hardware.delete_item(disk_drive)
            else:
                raise ValueUnsupportedError("drive type", drive_type,
                                            "CD-ROM ({0}) or hard disk ({1})"
                                            .format(self.RES_MAP['cdrom'],
                                                    self.RES_MAP['harddisk']))

    def add_disk(self, file_path, file_id, disk_type, disk=None):
        """Add a new disk object to the VM or overwrite the provided one.

        :param str file_path: Path to disk image file
        :param str file_id: Identifier string for the file/disk mapping
        :param str disk_type: 'harddisk' or 'cdrom'
        :param disk: Existing disk object to overwrite
        :type disk: xml.etree.ElementTree.Element

        :return: New or updated disk object
        """
        if disk_type != 'harddisk':
            if disk is not None:
                logger.warning("CD-ROMs do not require a Disk element. "
                               "Existing element will be deleted.")
                if self.disk_section is not None:
                    self.disk_section.remove(disk)
                    if not self.disk_section.findall(self.DISK):
                        logger.warning("No Disks left - removing DiskSection")
                        self.envelope.remove(self.disk_section)
                        self.disk_section = None
                disk = None
            else:
                logger.debug("Not adding Disk element to OVF, as CD-ROMs "
                             "do not require a Disk")
            return disk

        self.disk_section = self.create_envelope_section_if_absent(
            self.DISK_SECTION,
            "Virtual disk information",
            attrib=self.DISK_SECTION_ATTRIB)

        logger.debug("Adding Disk to OVF")

        if disk is not None:
            disk_id = disk.get(self.DISK_ID)
            disk.clear()
        else:
            disk_id = file_id
            disk = ET.SubElement(self.disk_section, self.DISK)

        capacity = get_disk_capacity(file_path)
        self.set_capacity_of_disk(disk, capacity)

        disk.set(self.DISK_ID, disk_id)
        disk.set(self.DISK_FILE_REF, file_id)
        disk.set(self.DISK_FORMAT,
                 ("http://www.vmware.com/interfaces/"
                  "specifications/vmdk.html#streamOptimized"))
        return disk

    def add_controller_device(self, device_type, subtype, address,
                              ctrl_item=None):
        """Create a new IDE or SCSI controller, or update existing one.

        :param str device_type: ``'ide'`` or ``'scsi'``
        :param subtype: Subtype such as ``'virtio'`` (optional), or list
           of subtype values
        :param int address: Controller address such as 0 or 1 (optional)
        :param OVFItem ctrl_item: Existing controller device to update
          (optional)

        :return: New or updated controller device object
        """
        if ctrl_item is None:
            logger.info("Controller not found, adding new Item")
            (_, ctrl_item) = self.hardware.new_item(device_type)
            if address is None:
                # Find a controller address that isn't already used
                address_list = [
                    ci.get_value(self.ADDRESS) for
                    ci in self.hardware.find_all_items(device_type)]
                address = 0
                while str(address) in address_list:
                    address += 1
                logger.info("Selected address %s for new controller", address)
            if device_type == "scsi" and int(address) > 3:
                raise ValueTooHighError("SCSI controller address", address, 3)
            elif device_type == "ide" and int(address) > 1:
                raise ValueTooHighError("IDE controller address", address, 1)
            ctrl_item.set_property(self.ADDRESS, address)
            ctrl_item.set_property(self.ELEMENT_NAME, "{0} Controller"
                                   .format(device_type.upper()))
            ctrl_item.set_property(self.ITEM_DESCRIPTION,
                                   "{0} Controller {1}"
                                   .format(device_type.upper(), address))
        # Change subtype of existing controller or new controller
        if subtype is not None:
            ctrl_item.set_property(self.RESOURCE_SUB_TYPE, subtype)
        return ctrl_item

    def _create_new_disk_device(self, disk_type, address, name, ctrl_item):
        """Helper for :meth:`add_disk_device`, in the case of no prior Item."""
        ctrl_instance = ctrl_item.get_value(self.INSTANCE_ID)
        if address is None:
            logger.debug("Working to identify address of new disk")

            items = self.hardware.find_all_items(
                properties={self.PARENT: ctrl_instance})
            addresses = [item.get_value(self.ADDRESS_ON_PARENT) for
                         item in items]
            address = 0
            while str(address) in addresses:
                address += 1
            logger.warning("New disk address on parent not specified, "
                           "guessing it should be %s", address)

        ctrl_type = self.get_type_from_device(ctrl_item)
        # Make sure the address is valid!
        if ctrl_type == "scsi" and int(address) > 15:
            raise ValueTooHighError("disk address on SCSI controller",
                                    address, 15)
        elif ctrl_type == "ide" and int(address) > 1:
            raise ValueTooHighError("disk address on IDE controller",
                                    address, 1)

        if name is None:
            if disk_type == 'cdrom':
                name = "CD-ROM Drive"
            elif disk_type == 'harddisk':
                name = "Hard Disk Drive"
            else:
                # Should never get here!
                raise ValueUnsupportedError("disk type", disk_type,
                                            "'cdrom' or 'harddisk'")

        (_, disk_item) = self.hardware.new_item(disk_type)
        disk_item.set_property(self.ADDRESS_ON_PARENT, address)
        disk_item.set_property(self.PARENT, ctrl_instance)

        return disk_item, name

    def add_disk_device(self, disk_type, address, name, description,
                        disk, file_obj, ctrl_item, disk_item=None):
        """Create a new disk hardware device or overwrite an existing one.

        :param str disk_type: ``'harddisk'`` or ``'cdrom'``
        :param str address: Address on controller, such as "1:0" (optional)
        :param str name: Device name string (optional)
        :param str description: Description string (optional)
        :param disk: Disk object to map to this device
        :type disk: xml.etree.ElementTree.Element
        :param file_obj: File object to map to this device
        :type file_obj: xml.etree.ElementTree.Element
        :param OVFItem ctrl_item: Controller object to serve as parent
        :param OVFItem disk_item: Existing disk device to update instead of
          making a new device.

        :return: New or updated disk device object.
        """
        if disk_item is None:
            logger.info("Disk Item not found, adding new Item")
            disk_item, name = self._create_new_disk_device(
                disk_type, address, name, ctrl_item)
        else:
            logger.debug("Updating existing disk Item")

        # Make these changes to the disk Item regardless of new/existing
        disk_item.set_property(self.RESOURCE_TYPE, self.RES_MAP[disk_type])
        if disk_type == 'harddisk':
            # Link to the Disk we created
            disk_item.set_property(self.HOST_RESOURCE,
                                   (self.HOST_RSRC_DISK_REF +
                                    disk.get(self.DISK_ID)))
        else:
            # No Disk for CD-ROM; link to the File instead
            disk_item.set_property(self.HOST_RESOURCE,
                                   (self.HOST_RSRC_FILE_REF +
                                    file_obj.get(self.FILE_ID)))

        if name is not None:
            disk_item.set_property(self.ELEMENT_NAME, name)
        if description is not None:
            disk_item.set_property(self.ITEM_DESCRIPTION, description)

        return disk_item

    # Helper methods - for internal use only

    def untar(self, file_path):
        """Untar the OVF descriptor from an .ova to the working directory.

        :param str file_path: OVA file path
        :raise VMInitError: if the given file does not represent a valid
          OVA archive.
        :return: Path to extracted OVF descriptor
        """
        logger.verbose("Untarring %s to working directory %s",
                       file_path, self.working_dir)

        try:
            tarf = tarfile.open(file_path, 'r')
        except (EOFError, tarfile.TarError) as e:
            raise VMInitError(1, "Could not untar {0}: {1}"
                              .format(file_path, e.args))

        try:
            # The OVF standard says, with regard to OVAs:
            # ...the files shall be in the following order inside the archive:
            # 1) OVF descriptor
            # 2) OVF manifest (optional)
            # 3) OVF certificate (optional)
            # 4) The remaining files shall be in the same order as listed
            #    in the References section...
            # 5) OVF manifest (optional)
            # 6) OVF certificate (optional)
            #
            # For now we just validate #1.
            if not tarf.getmembers():
                raise VMInitError(1, "No files to untar from {0}!"
                                  .format(file_path))
            ovf_descriptor = tarf.getmembers()[0]
            if os.path.splitext(ovf_descriptor.name)[1] != '.ovf':
                raise VMInitError(1,
                                  "First file in {0} is '{1}' but it should "
                                  "have been an OVF file - OVA is invalid!"
                                  .format(file_path, ovf_descriptor.name))
            # Make sure the provided file doesn't contain any malicious paths
            # http://stackoverflow.com/questions/8112742/
            for n in tarf.getnames():
                logger.debug("Examining path of %s prior to untar", n)
                if not (os.path.abspath(os.path.join(self.working_dir, n))
                        .startswith(self.working_dir)):
                    raise VMInitError(1, "Tar file contains malicious/unsafe "
                                      "file path '{0}'!".format(n))

            # TODO: In theory we could read the ovf descriptor XML directly
            # from the TAR and not need to even extract this file to disk...
            tarf.extract(ovf_descriptor, path=self.working_dir)
            logger.verbose(
                "Extracted OVF descriptor from %s to working dir %s",
                file_path, self.working_dir)
        finally:
            tarf.close()

        # Find the OVF file
        return os.path.join(self.working_dir, ovf_descriptor.name)

    def generate_manifest(self, ovf_file):
        """Construct the manifest file for this package, if possible.

        :param str ovf_file: OVF descriptor file path
        :returns: True if the manifest was successfully generated,
          False if not successful (such as if checksum helper tools are
          unavailable).
        """
        (prefix, _) = os.path.splitext(ovf_file)
        logger.verbose("Generating manifest for %s", ovf_file)
        manifest = prefix + '.mf'
        # TODO: OVF 2.0 uses SHA256 instead of SHA1.
        sha1sum = get_checksum(ovf_file, 'sha1')
        with open(manifest, 'wb') as f:
            f.write("SHA1({file})= {sum}\n"
                    .format(file=os.path.basename(ovf_file), sum=sha1sum)
                    .encode('utf-8'))
            # Checksum all referenced files as well
            for file_obj in self.references.findall(self.FILE):
                file_name = file_obj.get(self.FILE_HREF)
                file_ref = self._file_references[file_name]
                try:
                    file_obj = file_ref.open('rb')
                    sha1sum = get_checksum(file_obj, 'sha1')
                finally:
                    file_ref.close()

                f.write("SHA1({file})= {sum}\n"
                        .format(file=file_name, sum=sha1sum)
                        .encode('utf-8'))

        logger.debug("Manifest generated successfully")
        return True

    def tar(self, ovf_descriptor, tar_file):
        """Create a .ova tar file based on the given OVF descriptor.

        :param str ovf_descriptor: File path for an OVF descriptor
        :param str tar_file: File path for the desired OVA archive.
        """
        logger.verbose("Creating tar file %s", tar_file)

        (prefix, _) = os.path.splitext(ovf_descriptor)

        if self.input_file == tar_file:
            # We're about to overwrite the input OVA with a new OVA.
            # (Python tarfile module doesn't support in-place edits.)
            # Any files that we need to carry over need to be extracted NOW!
            logger.verbose("Extracting files from %s before overwriting it.",
                           self.input_file)
            for filename in self._file_references.keys():
                file_ref = self._file_references[filename]
                if file_ref.file_path is None:
                    file_ref.copy_to(self.working_dir)
                    self._file_references[filename] = FileOnDisk(
                        self.working_dir, filename)

        # Be sure to dereference any links to the actual file content!
        with closing(tarfile.open(tar_file, 'w', dereference=True)) as tarf:
            # OVF is always first
            logger.verbose("Adding %s to %s", ovf_descriptor, tar_file)
            tarf.add(ovf_descriptor, os.path.basename(ovf_descriptor))
            # Add manifest if present
            manifest_path = prefix + '.mf'
            if os.path.exists(manifest_path):
                logger.verbose("Adding manifest to %s", tar_file)
                tarf.add(manifest_path, os.path.basename(manifest_path))
            if os.path.exists("{0}.cert".format(prefix)):
                logger.warning("Don't know how to re-sign a certificate file, "
                               "so the existing certificate will be omitted "
                               "from %s.", tar_file)
            # Add all other files mentioned in the OVF
            for file_obj in self.references.findall(self.FILE):
                file_name = file_obj.get(self.FILE_HREF)
                file_ref = self._file_references[file_name]
                file_ref.add_to_archive(tarf)
                logger.verbose("Added %s to %s", file_name, tar_file)

    def create_envelope_section_if_absent(self, section_tag, info_string,
                                          attrib=None):
        """If the OVF doesn't already have the given Section, create it.

        :param str section_tag: XML tag of the desired section.
        :param str info_string: Info string to set if a new Section is created.
        :param dict attrib: Attributes to filter by when looking for any
          existing section (optional).
        :return: Section element that was found or created
        """
        section = self.find_child(self.envelope, section_tag, attrib=attrib)
        if section is not None:
            return section

        logger.info("No existing %s. Creating it.", XML.strip_ns(section_tag))
        if attrib:
            section = ET.Element(section_tag, attrib=attrib)
        else:
            section = ET.Element(section_tag)
        # Section elements may be in arbitrary order relative to one another,
        # but they MUST come after the References and before the VirtualSystem.
        # We'll construct them immediately before the VirtualSystem.
        i = 0
        for child in list(self.envelope):
            if child.tag == self.VIRTUAL_SYSTEM:
                break
            i += 1
        self.envelope.insert(i, section)

        # All Sections must have an Info child
        self.set_or_make_child(section, self.INFO, info_string)

        return section

    def set_product_section_child(self, child_tag, child_text):
        """If the OVF doesn't already have the given Section, create it.

        :param str child_tag: XML tag of the product section child element.
        :param str child_text: Text to set for the child element.
        :return: The product section element that was updated or created
        """
        if self.product_section is None:
            self.product_section = self.set_or_make_child(
                self.virtual_system, self.PRODUCT_SECTION,
                attrib=self.PRODUCT_SECTION_ATTRIB)
            # Any Section must have an Info as child
            self.set_or_make_child(self.product_section, self.INFO,
                                   "Product Information")
        self.set_or_make_child(self.product_section, child_tag, child_text)

        return self.product_section

    def find_parent_from_item(self, item):
        """Find the parent Item of the given Item.

        :param OVFItem item: Item whose parent is desired
        :return: :class:`OVFItem` representing the parent device, or None
        """
        if item is None:
            return None

        parent_instance = item.get_value(self.PARENT)
        if parent_instance is None:
            logger.error("Provided Item has no RASD:Parent element?")
            return None

        return self.hardware.find_item(
            properties={self.INSTANCE_ID: parent_instance})

    def find_item_from_disk(self, disk):
        """Find the disk Item that references the given Disk.

        :param xml.etree.ElementTree.Element disk: Disk element
        :return: :class:`OVFItem` instance, or None
        """
        if disk is None:
            return None

        disk_id = disk.get(self.DISK_ID)

        match = self.hardware.find_item(
            properties={
                self.HOST_RESOURCE: (self.HOST_RSRC_DISK_REF + disk_id)
            })
        if not match:
            match = self.hardware.find_item(
                properties={
                    self.HOST_RESOURCE: (self.OLD_HOST_RSRC_DISK_REF + disk_id)
                })
        return match

    def find_item_from_file(self, file_obj):
        """Find the disk Item that references the given File.

        :param xml.etree.ElementTree.Element file_obj: File element
        :return: :class:`OVFItem` instance, or None.
        """
        if file_obj is None:
            return None

        file_id = file_obj.get(self.FILE_ID)
        match = self.hardware.find_item(
            properties={
                self.HOST_RESOURCE: (self.HOST_RSRC_FILE_REF + file_id)
            })
        if not match:
            match = self.hardware.find_item(
                properties={
                    self.HOST_RESOURCE: (self.OLD_HOST_RSRC_FILE_REF + file_id)
                })
        return match

    def find_disk_from_file_id(self, file_id):
        """Find the Disk that uses the given file_id for backing.

        :param str file_id: File identifier string
        :return: Disk element matching the file, or None
        """
        if file_id is None or self.disk_section is None:
            return None

        return self.find_child(self.disk_section, self.DISK,
                               attrib={self.DISK_FILE_REF: file_id})

    def find_empty_drive(self, disk_type):
        """Find a disk device that exists but contains no data.

        :param str disk_type: Either 'cdrom' or 'harddisk'
        :return: Hardware device object, or None.
        """
        if disk_type == 'cdrom':
            # Find a drive that has no HostResource property
            return self.hardware.find_item(
                resource_type=disk_type,
                properties={self.HOST_RESOURCE: None})
        elif disk_type == 'harddisk':
            # All harddisk items must have a HostResource, so we need a
            # different way to indicate an empty drive. By convention,
            # we do this with a small placeholder disk (one with a Disk entry
            # but no corresponding File included in the OVF package).
            if self.disk_section is None:
                logger.verbose("No DiskSection, so no placeholder disk!")
                return None
            for disk in self.disk_section.findall(self.DISK):
                file_id = disk.get(self.DISK_FILE_REF)
                if file_id is None:
                    # Found placeholder disk!
                    # Now find the drive that's using this disk.
                    return self.find_item_from_disk(disk)
            logger.verbose("No placeholder disk found.")
            return None
        else:
            raise ValueUnsupportedError("drive type",
                                        disk_type,
                                        "'cdrom' or 'harddisk'")

    def find_device_location(self, device):
        """Find the controller type and address of a given device object.

        :param OVFItem device: Hardware device object.
        :returns: ``(type, address)``, such as ``("ide", "1:0")``.
        """
        controller = self.find_parent_from_item(device)
        if controller is None:
            raise LookupError("No parent controller for device?")
        return (self.get_type_from_device(controller),
                (controller.get_value(self.ADDRESS) + ':' +
                 device.get_value(self.ADDRESS_ON_PARENT)))

    def get_id_from_disk(self, disk):
        """Get the identifier string associated with the given Disk object.

        :param disk: Disk object to inspect
        :type disk: xml.etree.ElementTree.Element
        :rtype: string
        """
        return disk.get(self.DISK_ID)

    def get_capacity_from_disk(self, disk):
        """Get the capacity of the given Disk in bytes.

        :param disk: Disk element to inspect
        :type disk: xml.etree.ElementTree.Element
        :rtype: int
        """
        cap = int(disk.get(self.DISK_CAPACITY))
        cap_units = disk.get(self.DISK_CAP_UNITS, 'byte')
        return byte_count(cap, cap_units)

    def set_capacity_of_disk(self, disk, capacity_bytes):
        """Set the storage capacity of the given Disk.

        Tries to use the most human-readable form possible (i.e., 8 GiB
        instead of 8589934592 bytes).

        :param disk: Disk to update
        :type disk: xml.etree.ElementTree.Element
        :param int capacity_bytes: Disk capacity, in bytes
        """
        if self.ovf_version < 1.0:
            # In OVF 0.9 only bytes is supported as a unit
            disk.set(self.DISK_CAPACITY, capacity_bytes)
        else:
            (capacity, cap_units) = factor_bytes(capacity_bytes)
            disk.set(self.DISK_CAPACITY, capacity)
            disk.set(self.DISK_CAP_UNITS, cap_units)


if __name__ == "__main__":
    import doctest   # pylint: disable=wrong-import-position,wrong-import-order
    doctest.testmod()
