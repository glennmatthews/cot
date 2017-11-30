#!/usr/bin/env python
#
# ovf.py - Class for OVF/OVA handling
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Module for handling OVF and OVA virtual machine description files.

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
from xml.etree.ElementTree import ParseError
import textwrap

from COT.xml_file import XML
from COT.data_validation import (
    match_or_die, check_for_conflict, file_checksum,
    ValueTooHighError, ValueUnsupportedError, canonicalize_nic_subtype,
)
from COT.file_reference import FileReference
from COT.platforms import Platform
from COT.disks import DiskRepresentation
from COT.utilities import pretty_bytes, tar_entry_size

from ..vm_description import VMDescription, VMInitError
from .name_helper import name_helper, CIM_URI
from .hardware import OVFHardware, OVFHardwareDataError
from .item import list_union
from .utilities import (
    int_bytes_to_programmatic_units, parse_manifest, programmatic_bytes_to_int,
)

logger = logging.getLogger(__name__)


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
      network_descriptions
      system_types
      version_short
      version_long
    """

    # API methods to be called by clients

    @staticmethod
    def detect_type_from_name(filename):
        """Check the given filename to see if it looks like a type we support.

        For our purposes, the file needs to match ".ov[af]" to appear to be
        an OVF/OVA file. We also support names like "foo.ovf.20150101" as those
        have been seen in the wild.

        Does not check file contents, as the given filename may not yet exist.

        Args:
          filename (str): File name/path

        Returns:
          str: '.ovf', '.box' or '.ova'

        Raises:
          ValueUnsupportedError: if filename doesn't match ovf/ova
        """
        # We don't care about any directory path
        filename = os.path.basename(filename)
        extension = os.path.splitext(filename)[1]

        if extension == ".ovf" or extension == ".ova" or extension == ".box":
            return extension
        # Some sources of files are not good about preserving the extension
        # and hence tend to append additional extensions - while this may open
        # us to incorrect behavior (assuming that 'foo.ovf.zip' is a valid OVF
        # when it's probably a zip of an OVF) we'll err on the side of
        # accepting too much rather than incorrectly rejecting something like
        # "foo.ova.2014.05.06A" that's just lazily named.
        match = re.search(r"(\.ov[fa])[^a-zA-Z0-9]", filename)
        if match:
            extension = match.group(1)
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

        Args:
          input_file (str): Path to an OVF descriptor or OVA file.

        Returns:
          str: OVF descriptor path
        """
        extension = self.detect_type_from_name(input_file)
        if extension == '.ova' or extension == '.box':
            # Untar the ova to our working directory
            return self.untar(input_file)
        elif extension == '.ovf':
            return input_file
        else:
            return None

    def __init__(self, input_file, output_file):
        """Open the specified OVF and read its XML into memory.

        Args:
          input_file (str): Data file to read in.
          output_file (str): File name to write to. If this VM is read-only,
              (there will never be an output file) this value should be
              ``None``; if the output filename is not yet known, use ``""``
              and subsequently set :attr:`output_file` when it is determined.

        Raises:
          VMInitError:
              * if the OVF descriptor cannot be located
              * if an XML parsing error occurs
              * if the XML is not actually an OVF descriptor
              * if the OVF hardware validation fails
          Exception: will call :meth:`destroy` to clean up before reraising
              any exception encountered.
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
                    "File does not appear to be an OVA or OVF",
                    input_file)

            # Open the provided OVF
            try:
                XML.__init__(self, self.ovf_descriptor)
            except ParseError as exc:
                raise VMInitError(2,
                                  "XML error in parsing file: " + str(exc),
                                  self.ovf_descriptor)

            # Quick sanity check before we go any further:
            if ((not re.search(r"Envelope", self.root.tag)) or
                    (XML.strip_ns(self.root.tag) != 'Envelope')):
                raise VMInitError(
                    2,
                    "File does not appear to be an OVF descriptor - "
                    "expected top-level element {0} but found {1} instead"
                    .format('Envelope', self.root.tag),
                    self.ovf_descriptor)

            self._ovf_version = None
            self.name_helper = name_helper(self.ovf_version)

            for (prefix, uri) in self.NSM.items():
                ET.register_namespace(prefix, uri)

            # Register additional non-standard namespaces we're aware of:
            ET.register_namespace('vmw', "http://www.vmware.com/schema/ovf")
            ET.register_namespace('vbox',
                                  "http://www.virtualbox.org/ovf/machine")
            ET.register_namespace(
                'pasd',
                CIM_URI + "/cim-schema/2/CIM_ProcessorAllocationSettingData")

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
            except OVFHardwareDataError as exc:
                raise VMInitError(1,
                                  "OVF descriptor is invalid: {0}".format(exc),
                                  self.ovf_descriptor)

            assert self.platform

            self.file_references = self._init_check_file_entries()
            """Dictionary of FileReferences for this package.

            Does not include the manifest file."""

        except Exception:
            self.destroy()
            raise

    def _compare_file_lists(self, descriptor_file_list, manifest_file_list):
        """Helper for _init_check_file_entries method.

        Args:
          descriptor_file_list (list): List of file names derived from the
            OVF descriptor.
          manifest_file_list (list): List of file names derived from the
            manifest file (minus the descriptor itself).
        """
        if not manifest_file_list:
            return

        descriptor_in_manifest = False
        # DSP0243 2.1.0: "The manifest file shall contain SHA digests for all
        #                 distinct files referenced in the References element
        #                 of the OVF descriptor and for no other files."
        for filename in manifest_file_list:
            if filename == os.path.basename(self.ovf_descriptor):
                # Manifest should reference the descriptor, but of course the
                # descriptor does not reference itself
                descriptor_in_manifest = True
            elif filename not in descriptor_file_list:
                logger.error("The manifest lists file '%s' but the OVF"
                             " descriptor does not include it in its"
                             " References section", filename)
        for filename in descriptor_file_list:
            if filename not in manifest_file_list:
                logger.error("The OVF descriptor references file '%s' but"
                             " this file is not included in the manifest",
                             filename)

        if not descriptor_in_manifest:
            logger.error("The manifest does not list the OVF descriptor")

    def _init_check_file_entries(self):
        """Check files described in the OVF and store file references.

        Also compare the referenced files against the manifest, if any.

        Returns:
            dict: File HREF (file name) --> :class:`~COT.FileReference` object.
              Note that this does *not* include the OVF manifest file.
        """
        descriptor_files = dict(
            [(elem.get(self.FILE_HREF), elem.get(self.FILE_SIZE)) for
             elem in self.references.findall(self.FILE)])

        if self.input_file == self.ovf_descriptor:
            # Check files in the directory referenced by the OVF descriptor
            input_path = os.path.dirname(os.path.abspath(self.ovf_descriptor))
        else:
            # OVA - check contents of TAR file.
            input_path = self.input_file

        file_references = {}

        mf_filename = os.path.splitext(
            os.path.basename(self.ovf_descriptor))[0] + ".mf"
        manifest_entries = {}
        try:
            # We don't store the manifest file itself in file_references,
            # as it's basically a read-once file and storing it in the file
            # references causes much confusion when writing back out to
            # generate the OVF descriptor and manifest file.
            manifest_file = FileReference.create(input_path, mf_filename)
            with manifest_file.open('rb') as file_obj:
                manifest_text = file_obj.read().decode()
            manifest_entries = parse_manifest(manifest_text)
        except IOError:
            logger.debug("Manifest file is missing or unreadable.")

        self._compare_file_lists(descriptor_files.keys(),
                                 manifest_entries.keys())

        # Check the checksum of the descriptor itself
        # We don't store this in file_references as that would be
        # prone to self-recursion.
        m_algo, m_cksum = manifest_entries.get(
            os.path.basename(self.ovf_descriptor), (None, None))
        if m_algo and m_algo != self.checksum_algorithm:
            # TODO: log a warning? Discard the checksum?
            pass
        FileReference.create(
            input_path, os.path.basename(self.ovf_descriptor),
            checksum_algorithm=self.checksum_algorithm,
            expected_checksum=m_cksum)

        # Now check the checksum of the other files
        for file_href, file_size in descriptor_files.items():
            m_algo, m_cksum = manifest_entries.get(file_href, (None, None))
            if m_algo and m_algo != self.checksum_algorithm:
                # TODO: log a warning? Discard the checksum?
                pass
            try:
                file_references[file_href] = FileReference.create(
                    input_path, file_href,
                    checksum_algorithm=self.checksum_algorithm,
                    expected_checksum=m_cksum,
                    expected_size=file_size)
            except IOError:
                logger.error("File '%s' referenced in the OVF descriptor "
                             "does not exist.", file_href)
                continue

        return file_references

    @property
    def output_file(self):
        """OVF or OVA file that will be created or updated by :meth:`write`.

        Raises:
          ValueUnsupportedError: if :func:`detect_type_from_name` fails
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
            logger.debug("Root namespace is " + root_namespace)
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
                    "File has an Envelope but it is in unknown namespace '{0}'"
                    .format(root_namespace),
                    self.ovf_descriptor)
        return self._ovf_version

    @property
    def checksum_algorithm(self):
        """The preferred file checksum algorithm for this OVF."""
        if self.ovf_version >= 2.0:
            # OVF 2.x uses SHA256 for manifest
            return 'sha256'
        else:
            # OVF 0.x and 1.x use SHA1
            return 'sha1'

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
        self.product_section = self._ensure_section(
            self.PRODUCT_SECTION,
            "Product Information",
            attrib=self.PRODUCT_SECTION_ATTRIB,
            parent=self.virtual_system)
        if self.product_class:
            logger.debug("Changing product class from '%s' to '%s'",
                         self.product_class, product_class)
        self.product_section.set(self.PRODUCT_CLASS, product_class)
        self._product_class = product_class

        # Change platform as well!
        self._platform = None
        assert self.platform

    @property
    def platform(self):
        """The platform type, as determined from the OVF descriptor.

        This will be the class :class:`~COT.platforms.Platform` or
        a more-specific subclass if recognized as such.
        """
        if self._platform is None:
            self._platform = Platform.for_product_string(self.product_class)
            logger.info("OVF product class %s --> platform %s",
                        self.product_class, self.platform)
        return self._platform

    def validate_hardware(self):
        """Check sanity of hardware properties for this VM/product/platform.

        Returns:
          bool: ``True`` if hardware is sane, ``False`` if not.
        """
        result = True

        # TODO refactor to share logic with profile_info_list()
        profile_ids = self.config_profiles
        if not profile_ids:
            profile_ids = [None]

        plat = self.platform

        def _validate_helper(label, validator, *args):
            """Call validation function, catch errors and warn user instead.

            Args:
              label (str): Label to prepend to any warning messages
              validator (function): Validation function to call.
              *args (list): Arguments to validation function.

            Returns:
              bool: True if valid, False if invalid
            """
            try:
                validator(*args)
                return True
            except ValueUnsupportedError as exc:
                logger.warning(label + str(exc))
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
                megabytes = (programmatic_bytes_to_int(
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

        Array of dicts (one per property) with the keys ``"key"``, ``"value"``,
        ``"qualifiers"``, ``"type"``, ``"user_configurable"``, ``"label"``,
        and ``"description"``.
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
                'user_configurable': elem.get(self.PROP_USER_CONFIGABLE, ""),
                'label': label,
                'description': descr,
            })

        return result

    @property
    def environment_transports(self):
        """The list of environment transport method strings."""
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
        logger.debug("Setting %s to '%s'", self.ENVIRONMENT_TRANSPORT,
                     transports_string)
        self.virtual_hw_section.set(self.ENVIRONMENT_TRANSPORT,
                                    transports_string)

    @property
    def networks(self):
        """The list of network names currently defined in this VM."""
        if self.network_section is None:
            return []
        return [network.get(self.NETWORK_NAME) for
                network in self.network_section.findall(self.NETWORK)]

    @property
    def network_descriptions(self):
        """The list of network descriptions currently defined in this VM.

        Returns:
          list: List of network description strings
        """
        if self.network_section is None:
            return []
        return [network.findtext(self.NWK_DESC, "") for
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
        logger.debug("Setting VirtualSystemType to '%s'", type_string)
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
        logger.debug("Updating Product element in OVF")
        self._set_product_section_child(self.PRODUCT, product_string)

    @property
    def vendor(self):
        """Short descriptive vendor string (XML ``Vendor`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.VENDOR, None)
        return None

    @vendor.setter
    def vendor(self, vendor_string):
        logger.debug("Updating Vendor element in OVF")
        self._set_product_section_child(self.VENDOR, vendor_string)

    @property
    def version_short(self):
        """Short descriptive version string (XML ``Version`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.VERSION, None)
        return None

    @version_short.setter
    def version_short(self, version_string):
        logger.debug("Updating Version element in OVF")
        self._set_product_section_child(self.VERSION, version_string)

    @property
    def version_long(self):
        """Long descriptive version string (XML ``FullVersion`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.FULL_VERSION, None)
        return None

    @version_long.setter
    def version_long(self, version_string):
        logger.debug("Updating FullVersion element in OVF")
        self._set_product_section_child(self.FULL_VERSION, version_string)

    @property
    def product_url(self):
        """Product URL string (XML ``ProductUrl`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.PRODUCT_URL, None)
        return None

    @product_url.setter
    def product_url(self, product_url_string):
        logger.debug("Updating ProductUrl element in OVF")
        self._set_product_section_child(self.PRODUCT_URL, product_url_string)

    @property
    def vendor_url(self):
        """Vendor URL string (XML ``VendorUrl`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.VENDOR_URL, None)
        return None

    @vendor_url.setter
    def vendor_url(self, vendor_url_string):
        logger.debug("Updating VendorUrl element in OVF")
        self._set_product_section_child(self.VENDOR_URL, vendor_url_string)

    @property
    def application_url(self):
        """Application URL string (XML ``AppUrl`` element)."""
        if self.product_section is not None:
            return self.product_section.findtext(self.APPLICATION_URL, None)
        return None

    @application_url.setter
    def application_url(self, app_url_string):
        logger.debug("Updating AppUrl element in OVF")
        self._set_product_section_child(self.APPLICATION_URL, app_url_string)

    def __getattr__(self, name):
        """Transparently pass attribute lookups off to name_helper.

        Args:
          name (str): Attribute being looked up.

        Returns:
          Attribute value

        Raises:
          AttributeError: Magic methods (``__foo``) will not be passed
              through but will raise an AttributeError as usual.
        """
        # Don't pass 'special' attributes through to the helper
        if re.match(r"^__", name):
            raise AttributeError("'OVF' object has no attribute '{0}'"
                                 .format(name))
        return getattr(self.name_helper, name)

    def predicted_output_size(self):
        """Estimate how much disk space (in bytes) is needed to write out.

        Since OVA (TAR) is an uncompressed format, the disk space required
        is approximately the same for both OVF and OVA output. Thus we can
        provide this value even if :attr:`output_file` is ``None``.

        In the TAR format, each file in the archive has a 512-byte header
        and its total size is rounded up to a multiple of 512 bytes. The
        archive is terminated by 2 512-byte blocks filled with zero, and
        the overall archive file size is a multiple of 10 kiB.

        Returns:
          int: Estimated number of bytes consumed when writing out to
            :attr:`output_file` (plus any associated files).
        """
        # Size of the OVF descriptor
        needed = tar_entry_size(len(ET.tostring(self.root)))

        # Account for the size of all the referenced files
        manifest_size = 0
        for href, file_ref in self.file_references.items():
            # Approximate size of a manifest entry for this file
            if self.ovf_version >= 2.0:
                # SHA256(href)= <64 hex digits>
                # so 64 + href length + ~12 other characters
                manifest_size += 76 + len(href)
            else:
                # SHA1(href)= <40 hex digits>
                # so 40 + href length + ~10 other characters
                manifest_size += 50 + len(href)

            # Size of the file proper
            needed += tar_entry_size(file_ref.size)

        # Manifest file
        needed += tar_entry_size(manifest_size)

        # Archive end - two 512-byte records filled with zeros
        needed += 1024

        # Overall size must be a multiple of 10 kiB
        needed += (10240 - needed) % 10240

        logger.debug("Estimated output size is %s", pretty_bytes(needed))
        return needed

    def write(self):
        """Write OVF or OVA to :attr:`output_file`, if set."""
        if not self.output_file:
            return

        logger.info("Updating and validating internal data before writing"
                    " out to disk")
        prefix = os.path.splitext(self.output_file)[0]
        extension = self.output_extension

        # Update the XML ElementTree to reflect any hardware changes
        self.hardware.update_xml()

        # Validate the hardware to be written
        self.validate_hardware()

        # Make sure file references are correct:
        self._refresh_file_references()

        # Make sure all defined networks are actually used by NICs,
        # and delete any networks that are unused.
        self._refresh_networks()

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

            for file_ref in self.file_references.values():
                file_ref.copy_to(dest_dir)

            # Generate manifest
            self.generate_manifest(self.output_file)
        else:
            # We should never get here, but to be safe:
            raise NotImplementedError("Not sure how to write a '{0}' file"
                                      .format(extension))

    def _refresh_file_references(self):
        """Check all File entries to make sure they are valid and up to date.

        Helper method for :func:`write`.
        """
        # Refresh the file references
        to_delete = []
        for filename, file_ref in self.file_references.items():
            if file_ref.exists:
                file_ref.refresh()
            else:
                # file used to exist but no longer does??
                logger.error("Referenced file '%s' does not exist!", filename)
                to_delete.append(filename)

        for filename in to_delete:
            del self.file_references[filename]

        for file_elem in self.references.findall(self.FILE):
            href = file_elem.get(self.FILE_HREF)
            if href not in self.file_references:
                # TODO this should probably have a confirm() check...
                logger.notice("Removing reference to missing file %s", href)
                self.references.remove(file_elem)
                # TODO remove references to this file from Disk, Item?

        for filename, file_ref in self.file_references.items():
            file_elem = self.find_child(self.references, self.FILE,
                                        {self.FILE_HREF: filename})
            assert file_elem is not None
            file_elem.set(self.FILE_SIZE, str(file_ref.size))

            real_capacity = None

            disk_item = self.find_disk_from_file_id(
                file_elem.get(self.FILE_ID))

            if disk_item is not None:
                # We can't check disk capacity inside a tar file.
                # It seems wasteful to extract the disk file (could be
                # quite large) from the TAR just to check, so we don't.
                if file_ref.file_path is not None:
                    diskrep = DiskRepresentation.from_file(file_ref.file_path)
                    real_capacity = diskrep.capacity

            if disk_item is not None and real_capacity is not None:
                reported_capacity = str(self.get_capacity_from_disk(disk_item))
                if reported_capacity != real_capacity:
                    logger.warning(
                        "Capacity of disk '%s' seems to have changed "
                        "from %s (reported in the original OVF) "
                        "to %s (actual capacity). "
                        "The updated OVF will reflect this change.",
                        filename, reported_capacity, real_capacity)
                    self.set_capacity_of_disk(disk_item, real_capacity)

    def _refresh_networks(self):
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
                logger.notice("Removing unused network %s", name)
                self.network_section.remove(net)
        # If all networks were removed, remove the NetworkSection too
        if not self.network_section.findall(self.NETWORK):
            logger.notice("No networks left - removing NetworkSection")
            self.envelope.remove(self.network_section)
            self.network_section = None

    def _info_string_header(self, width):
        """Generate OVF/OVA file header for :meth:`info_string`.

        Args:
          width (int): Line length to wrap to where possible.

        Returns:
          str: File header
        """
        str_list = []
        str_list.append('-' * width)
        str_list.append(self.input_file)
        if self.platform and self.platform.__class__ is not Platform:
            str_list.append("COT detected platform type: {0}"
                            .format(self.platform))
        str_list.append('-' * width)
        return '\n'.join(str_list)

    def _info_string_product(self, verbosity_option, wrapper):
        """Generate product information as part of :meth:`info_string`.

        Args:
          verbosity_option (str): 'brief', None (default), or 'verbose'
          wrapper (textwrap.TextWrapper): Helper object for wrapping text
              lines if needed.

        Returns:
          str: Product information
        """
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
        """Generate annotation information as part of :meth:`info_string`.

        Args:
          wrapper (textwrap.TextWrapper): Helper object for wrapping
              text lines if needed.

        Returns:
          str: Annotation information string, or None
        """
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
        """Generate EULA information as part of :meth:`info_string`.

        Args:
          verbosity_option (str): 'brief', None (default), or 'verbose'
          wrapper (textwrap.TextWrapper): Helper object for wrapping
              text lines if needed.

        Returns:
          str: EULA information
        """
        # An OVF may have zero, one, or more
        eula_header = False
        str_list = []
        for eula in self.find_all_children(self.virtual_system,
                                           self.EULA_SECTION,
                                           self.EULA_SECTION_ATTRIB):
            info = eula.find(self.INFO)
            lic = eula.find(self.EULA_LICENSE)
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

        Args:
          file_obj (xml.etree.ElementTree.Element): File to inspect

        Returns:
          tuple: (file_id, file_size, disk_id, disk_capacity, device_info)
        """
        # FILE_SIZE is optional
        reported_size = file_obj.get(self.FILE_SIZE)
        if reported_size is None:
            # TODO - check file size in working dir and/or tarfile
            file_size_str = ""
        else:
            file_size_str = pretty_bytes(reported_size)

        disk_obj = self.find_disk_from_file_id(file_obj.get(self.FILE_ID))
        if disk_obj is None:
            disk_id = ""
            disk_cap_string = ""
            device_item = self.find_item_from_file(file_obj)
        else:
            disk_id = disk_obj.get(self.DISK_ID)
            disk_cap_string = pretty_bytes(
                self.get_capacity_from_disk(disk_obj))
            device_item = self.find_item_from_disk(disk_obj)
        device_str = self.device_info_str(device_item)

        return (file_obj.get(self.FILE_ID),
                file_size_str,
                disk_id,
                disk_cap_string,
                device_str)

    def _info_string_files_disks(self, width, verbosity_option):
        """Describe files and disks as part of :meth:`info_string`.

        Args:
          width (int): Line length to wrap to where possible.
          verbosity_option (str): 'brief', None (default), or 'verbose'

        Returns:
          str: File/disk information string, or None
        """
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
            disk_cap_string = pretty_bytes(self.get_capacity_from_disk(disk))
            device_item = self.find_item_from_disk(disk)
            device_str = self.device_info_str(device_item)
            str_list.append(template.format("  (disk placeholder)",
                                            "--",
                                            disk_cap_string,
                                            device_str))
        return "\n".join(str_list)

    def _info_string_hardware(self, wrapper):
        """Describe hardware subtypes as part of :meth:`info_string`.

        Args:
          wrapper (textwrap.TextWrapper): Helper object for wrapping
              text lines if needed.

        Returns:
          str: Hardware information string, or None
        """
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

    def _info_string_networks(self, verbosity_option, wrapper):
        """Describe virtual networks as part of :meth:`info_string`.

        Args:
          verbosity_option (str): 'brief', None (default), or 'verbose'
          wrapper (textwrap.TextWrapper): Helper object for wrapping
              text lines if needed.

        Returns:
          str: Network information string, or None
        """
        if self.network_section is None:
            return None
        str_list = ["Networks:"]
        width = wrapper.width
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
        """Describe NICs as part of :meth:`info_string`.

        Args:
          verbosity_option (str): 'brief', None (default), or 'verbose'
          wrapper (textwrap.TextWrapper): Helper object for wrapping
              text lines if needed.

        Returns:
          str: NIC information string, or None
        """
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
        """Describe environment for :meth:`info_string`.

        Args:
          wrapper (textwrap.TextWrapper): Helper object for wrapping
              text lines if needed.

        Returns:
          str: Environment information string, or None
        """
        if not self.environment_transports:
            return None
        str_list = ["Environment:"]
        wrapper.initial_indent = '  '
        wrapper.subsequent_indent = '    '
        str_list.extend(wrapper.wrap(
            "Transport types: {0}"
            .format(" ".join(self.environment_transports))))
        return "\n".join(str_list)

    def _info_string_properties(self, verbosity_option, wrapper):
        """Describe config properties for :meth:`info_string`.

        Args:
          verbosity_option (str): 'brief', None (default), or 'verbose'
          wrapper (textwrap.TextWrapper): Helper object for wrapping
              text lines if needed.

        Returns:
          str: Property information string, or None
        """
        properties = self.environment_properties
        if not properties:
            return None
        str_list = ["Properties:"]
        max_key = 2 + max([len(str(ph['key'])) for ph in properties])
        max_label = max([len(str(ph['label'])) for ph in properties])
        max_value = max([len(str(ph['value'])) for ph in properties])
        width = wrapper.width
        if all(ph['label'] for ph in properties):
            max_width = max_label
        else:
            max_width = max(max_key, max_label)
        wrapper.initial_indent = '      '
        wrapper.subsequent_indent = '      '
        for propdict in properties:
            # If we have a label, and the terminal is wide enough,
            # display "<key> label value", else if no label, display
            # "<key> value", else only display "label value"
            if max_label > 0 and (max_key + max_label + max_value <
                                  width - 8):
                format_str = '  {key:{kw}}  {label:{lw}}  {val}'
                str_list.append(format_str.format(
                    key="<{0}>".format(propdict['key']),
                    kw=max_key,
                    label=propdict['label'],
                    lw=max_label,
                    val=('"{0}"'.format(propdict['value'])
                         if propdict['value'] is not None
                         else '--')))
            else:
                str_list.append('  {label:{width}}  {val}'.format(
                    label=(propdict['label'] if propdict['label']
                           else "<{0}>".format(propdict['key'])),
                    width=max_width,
                    val=('"{0}"'.format(propdict['value'])
                         if propdict['value'] is not None
                         else '--')))
            if verbosity_option == 'verbose':
                for line in propdict['description'].splitlines():
                    if not line:
                        str_list.append("")
                    else:
                        str_list.extend(wrapper.wrap(line))
        return "\n".join(str_list)

    def info_string(self, width=79, verbosity_option=None):
        """Get a descriptive string summarizing the contents of this OVF.

        Args:
          width (int): Line length to wrap to where possible.
          verbosity_option (str): 'brief', None (default), or 'verbose'

        Returns:
          str: Wrapped, appropriately verbose string.
        """
        # Supposedly it's quicker to construct a list of strings then merge
        # them all together with 'join()' rather than it is to repeatedly
        # append to an existing string with '+'.
        # I haven't profiled this to verify - it's fast enough for now.

        # Don't break in mid-word or on hyphens, as the usual case where
        # we may exceed the available width is URI literals, and there's
        # no ideal way to wrap these.
        wrapper = textwrap.TextWrapper(width=width,
                                       break_long_words=False,
                                       break_on_hyphens=False)

        # File description
        header = self._info_string_header(width)

        section_list = [
            self._info_string_product(verbosity_option, wrapper),
            self._info_string_annotation(wrapper),
            self._info_string_eula(verbosity_option, wrapper),
            self._info_string_files_disks(width, verbosity_option),
            self._info_string_hardware(wrapper),
            self.profile_info_string(width, verbosity_option),
            self._info_string_networks(verbosity_option, wrapper),
            self._info_string_nics(verbosity_option, wrapper),
            self._info_string_environment(wrapper),
            self._info_string_properties(verbosity_option, wrapper)
        ]
        # Discard empty sections
        section_list = [s for s in section_list if s]

        return header + '\n' + "\n\n".join(section_list)

    def device_info_str(self, device_item):
        """Get a one-line summary of a hardware device.

        Args:
          device_item (OVFItem): Device to summarize

        Returns:
          str: Descriptive string such as "harddisk @ IDE 1:0"
        """
        if device_item is None:
            return ""
        controller_item = self.find_parent_from_item(device_item)
        if controller_item is None:
            ctrl_type = "(?)"
            ctrl_addr = "?"
        else:
            ctrl_type = controller_item.hardware_type.upper()
            ctrl_addr = controller_item.get_value(self.ADDRESS)
        return "{0} @ {1} {2}:{3}".format(
            device_item.hardware_type,
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

        Args:
          width (int): Line length to wrap to if possible
          verbose (bool): if True, generate multiple lines per profile

        Returns:
          tuple: (header, list)
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
                mem_bytes = programmatic_bytes_to_int(
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
                pretty_bytes(mem_bytes),
                nics,
                serials,
                "{0:2} / {1:>9}".format(disk_count,
                                        pretty_bytes(disks_size))))
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

        Args:
          width (int): Line length to wrap to if possible
          verbosity_option (str): 'brief', None (default), or 'verbose'

        Returns:
          str: Appropriately formatted and verbose string.
        """
        header, str_list = self.profile_info_list(
            width, (verbosity_option != 'brief'))
        return "\n".join([header] + str_list)

    def create_configuration_profile(self, pid, label, description):
        """Create or update a configuration profile with the given ID.

        Args:
          pid (str): Profile identifier
          label (str): Brief descriptive label for the profile
          description (str): Verbose description of the profile
        """
        self.deploy_opt_section = self._ensure_section(
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
        """Delete the profile with the given ID.

        Args:
          profile (str): Profile ID to delete.

        Raises:
          LookupError: if the profile does not exist.
        """
        cfg = self.find_child(self.deploy_opt_section, self.CONFIG,
                              attrib={self.CONFIG_ID: profile})
        if cfg is None:
            raise LookupError("No such configuration profile '{0}'"
                              .format(profile))
        logger.notice("Deleting configuration profile %s", profile)

        # Delete references to this profile from the hardware
        items = self.hardware.find_all_items(profile_list=[profile])
        logger.debug("Removing profile %s from %s hardware items",
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

        Args:
          cpus (int): Number of CPUs
          profile_list (list): Change only the given profiles
        """
        logger.debug("Updating CPU count in OVF under profile %s to %s",
                     profile_list, cpus)
        self.platform.validate_cpu_count(cpus)
        self.hardware.set_value_for_all_items('cpu',
                                              self.VIRTUAL_QUANTITY, cpus,
                                              profile_list,
                                              create_new=True)

    def set_memory(self, megabytes, profile_list):
        """Set the amount of RAM, in megabytes.

        Args:
          megabytes (int): Memory value, in megabytes
          profile_list (list): Change only the given profiles
        """
        logger.debug("Updating RAM in OVF under profile %s to %s",
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

        Args:
          type_list (list): NIC hardware type(s)
          profile_list (list): Change only the given profiles.
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

        Args:
          profile_list (list): Profile(s) of interest.

        Returns:
          dict: ``{ profile_name : nic_count }``
        """
        return self.hardware.get_item_count_per_profile('ethernet',
                                                        profile_list)

    def set_nic_count(self, count, profile_list):
        """Set the given profile(s) to have the given number of NICs.

        Args:
          count (int): number of NICs
          profile_list (list): Change only the given profiles
        """
        logger.debug("Updating NIC count in OVF under profile %s to %s",
                     profile_list, count)
        self.platform.validate_nic_count(count)
        self.hardware.set_item_count_per_profile('ethernet', count,
                                                 profile_list)

    def create_network(self, label, description):
        """Define a new network with the given label and description.

        Also serves to update the description of an existing network label.

        Args:
          label (str): Brief label for the network
          description (str): Verbose description of the network
        """
        self.network_section = self._ensure_section(
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

        Args:
          network_list (list): List of networks to map NICs to
          profile_list (list): Change only the given profiles
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

        Args:
          mac_list (list): List of MAC addresses to assign to NICs
          profile_list (list): Change only the given profiles
        """
        self.hardware.set_item_values_per_profile('ethernet',
                                                  self.ADDRESS,
                                                  mac_list,
                                                  profile_list,
                                                  default=mac_list[-1])

    def set_nic_names(self, name_list, profile_list):
        """Set the device names for NICs under the given profile(s).

        Args:
          name_list (list): List of names to assign.
          profile_list (list): Change only the given profiles
        """
        self.hardware.set_item_values_per_profile('ethernet',
                                                  self.ELEMENT_NAME,
                                                  name_list,
                                                  profile_list)

    def get_serial_count(self, profile_list):
        """Get the number of serial ports under the given profile(s).

        Args:
          profile_list (list): Profile(s) of interest.

        Returns:
          dict: ``{ profile_name : serial_count }``
        """
        return self.hardware.get_item_count_per_profile('serial', profile_list)

    def set_serial_count(self, count, profile_list):
        """Set the given profile(s) to have the given number of serial ports.

        Args:
          count (int): Number of serial ports
          profile_list (list): Change only the given profiles
        """
        logger.debug("Updating serial port count under profile %s to %s",
                     profile_list, count)
        self.hardware.set_item_count_per_profile('serial', count, profile_list)

    def set_serial_connectivity(self, conn_list, profile_list):
        """Set the serial port connectivity under the given profile(s).

        Args:
          conn_list (list): List of connectivity strings
          profile_list (list): Change only the given profiles
        """
        self.hardware.set_item_values_per_profile('serial',
                                                  self.ADDRESS, conn_list,
                                                  profile_list, default="")

    def get_serial_connectivity(self, profile):
        """Get the serial port connectivity strings under the given profile.

        Args:
          profile (str): Profile of interest.

        Returns:
          list: connectivity strings
        """
        return [item.get_value(self.ADDRESS) for item in
                self.hardware.find_all_items('serial', profile_list=[profile])]

    def set_scsi_subtypes(self, type_list, profile_list):
        """Set the device subtype(s) for the SCSI controller(s).

        Args:
          type_list (list): SCSI subtype string list
          profile_list (list): Change only the given profiles
        """
        # TODO validate supported types by platform
        self.hardware.set_value_for_all_items('scsi',
                                              self.RESOURCE_SUB_TYPE,
                                              type_list,
                                              profile_list)

    def set_ide_subtypes(self, type_list, profile_list):
        """Set the device subtype(s) for the IDE controller(s).

        Args:
          type_list (list): IDE subtype string list
          profile_list (list): Change only the given profiles
        """
        # TODO validate supported types by platform
        self.hardware.set_value_for_all_items('ide',
                                              self.RESOURCE_SUB_TYPE,
                                              type_list,
                                              profile_list)

    def get_property_value(self, key):
        """Get the value of the given property.

        Args:
          key (str): Property identifier

        Returns:
          str: Value of this property as a string, or ``None``
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

        Args:
          prop (xml.etree.ElementTree.Element): Existing Property element.
          value (str): Proposed value to set for this property.

        Returns:
          str: the value, potentially canonicalized.

        Raises:
          ValueUnsupportedError: if the value does not meet criteria.
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
            match = re.search(r"MaxLen\((\d+)\)", prop_qual)
            if match:
                max_len = int(match.group(1))
                if len(value) > max_len:
                    raise ValueUnsupportedError(
                        key, value, "string no longer than {0} characters"
                        .format(max_len))
            match = re.search(r"MinLen\((\d+)\)", prop_qual)
            if match:
                min_len = int(match.group(1))
                if len(value) < min_len:
                    raise ValueUnsupportedError(
                        key, value, "string no shorter than {0} characters"
                        .format(min_len))

        return value

    def set_property_value(self, key, value,
                           user_configurable=None, property_type=None,
                           label=None, description=None):
        """Set the value of the given property (converting value if needed).

        Args:
          key (str): Property identifier
          value (object): Value to set for this property
          user_configurable (bool): Should this property be configurable at
              deployment time by the user?
          property_type (str): Value type - 'string' or 'boolean'
          label (str): Brief explanatory label for this property
          description (str): Detailed description of this property

        Returns:
          str: the (converted) value that was set.

        Raises:
          NotImplementedError: if :attr:`ovf_version` is less than 1.0;
              OVF version 0.9 is not currently supported.
        """
        if self.ovf_version < 1.0:
            raise NotImplementedError("No support for setting environment "
                                      "properties under OVF v0.9")
        self.product_section = self._ensure_section(
            self.PRODUCT_SECTION,
            "Product Information",
            attrib=self.PRODUCT_SECTION_ATTRIB,
            parent=self.virtual_system)
        prop = self.find_child(self.product_section, self.PROPERTY,
                               attrib={self.PROP_KEY: key})
        if prop is None:
            prop = self.set_or_make_child(self.product_section, self.PROPERTY,
                                          attrib={self.PROP_KEY: key})
            # Properties *must* have a type to be valid
            if property_type is None:
                property_type = 'string'

        if user_configurable is not None:
            prop.set(self.PROP_USER_CONFIGABLE, str(user_configurable).lower())
        if property_type is not None:
            prop.set(self.PROP_TYPE, property_type)
            # Revalidate any existing value if not setting a new value
            if value is None:
                value = prop.get(self.PROP_VALUE)

        if value is not None:
            # Make sure the requested value is valid
            value = self._validate_value_for_property(prop, value)
            prop.set(self.PROP_VALUE, value)

        if label is not None:
            self.set_or_make_child(prop, self.PROPERTY_LABEL, label)
        if description is not None:
            self.set_or_make_child(prop, self.PROPERTY_DESC, description)

        return value

    def config_file_to_properties(self, file_path, user_configurable=None):
        """Import each line of a text file into a configuration property.

        Args:
          file_path (str): File name to import.
          user_configurable (bool): Should the resulting properties be
              configurable at deployment time by the user?

        Raises:
          NotImplementedError: if the :attr:`platform` for this OVF
              does not define
              :const:`~COT.platforms.Platform.LITERAL_CLI_STRING`
        """
        if not self.platform.LITERAL_CLI_STRING:
            raise NotImplementedError("no known support for literal CLI on " +
                                      str(self.platform))
        property_num = 0
        with open(file_path, 'r') as fileobj:
            for line in fileobj:
                line = line.strip()
                # Skip blank lines and comment lines
                if (not line) or line[0] == '!':
                    continue
                property_num += 1
                self.set_property_value(
                    "{0}-{1:04d}".format(self.platform.LITERAL_CLI_STRING,
                                         property_num),
                    line,
                    user_configurable)

    def convert_disk_if_needed(self, disk_image, kind):
        """Convert the disk to a more appropriate format if needed.

        * All hard disk files are converted to stream-optimized VMDK as it
          is the only format that VMware supports in OVA packages.
        * CD-ROM iso images are accepted without change.

        Args:
          disk_image (COT.disks.DiskRepresentation): Image to inspect and
              possibly convert
          kind (str): Image type (harddisk/cdrom)

        Returns:
          DiskRepresentation: :attr:`disk_image`, if no conversion was
          required, or a new :class:`~COT.disks.DiskRepresentation` instance
          representing a converted image that has been created in
          :attr:`output_dir`.
        """
        if kind != 'harddisk':
            logger.debug("No disk conversion needed")
            return disk_image

        # Convert hard disk to VMDK format, streamOptimized subformat
        if (disk_image.disk_format == 'vmdk' and
                disk_image.disk_subformat == 'streamOptimized'):
            logger.debug("No disk conversion needed")
            return disk_image

        logger.debug("Converting %s (%s, %s) to streamOptimized VMDK",
                     disk_image.path, disk_image.disk_format,
                     disk_image.disk_subformat)
        return disk_image.convert_to(new_format='vmdk',
                                     new_subformat='streamOptimized',
                                     new_directory=self.working_dir)

    def search_from_filename(self, filename):
        """From the given filename, try to find any existing objects.

        This implementation uses the given :attr:`filename` to find a matching
        ``File`` in the OVF, then using that to find a matching ``Disk`` and
        ``Item`` entries.

        Args:
          filename (str): Filename to search from

        Returns:
          tuple: ``(file, disk, ctrl_item, disk_item)``, any or all of which
          may be ``None``

        Raises:
          LookupError: If the ``disk_item`` is found but no ``ctrl_item`` is
              found to be its parent.
        """
        file_obj = None
        disk = None
        ctrl_item = None
        disk_item = None

        logger.debug("Looking for existing disk info based on filename %s",
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

        Args:
          file_id (str): File ID to search from

        Returns:
          tuple: ``(file, disk, ctrl_item, disk_item)``, any or all of which
              may be ``None``

        Raises:
          LookupError: If the ``disk`` entry is found but no corresponding
              ``file`` is found.
          LookupError: If the ``disk_item`` is found but no ``ctrl_item`` is
              found to be its parent.
        """
        if file_id is None:
            return (None, None, None, None)

        logger.debug(
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

        Args:
          controller (str): ``'ide'`` or ``'scsi'``
          address (str): Device address such as ``'1:0'``

        Returns:
          tuple: ``(file, disk, ctrl_item, disk_item)``, any or all of which
          may be ``None``
        """
        if controller is None or address is None:
            return (None, None, None, None)

        logger.debug("Looking for existing disk information based on "
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
            logger.error(
                "Unrecognized HostResource format '%s'; unable to identify "
                "which File and Disk are associated with this disk Item",
                host_resource)

        return (file_obj, disk, ctrl_item, disk_item)

    def find_open_controller(self, controller_type):
        """Find the first open slot on a controller of the given type.

        Args:
          controller_type (str): ``'ide'`` or ``'scsi'``

        Returns:
          tuple: ``(ctrl_item, address_string)`` or ``(None, None)``
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
                logger.debug("Controller address %s is already full",
                             ctrl_addr)
            else:
                logger.verbose("Found open slot %s:%s for %s controller",
                               ctrl_addr, disk_addr, controller_type)
                return (ctrl_item, "{0}:{1}".format(ctrl_addr, disk_addr))

        logger.notice("No open controller found")
        return (None, None)

    def get_id_from_file(self, file_obj):
        """Get the file ID from the given opaque file object.

        Args:
          file_obj (xml.etree.ElementTree.Element): 'File' element

        Returns:
          str: 'id' attribute value of this element
        """
        return file_obj.get(self.FILE_ID)

    def get_path_from_file(self, file_obj):
        """Get the file path from the given opaque file object.

        Args:
          file_obj (xml.etree.ElementTree.Element): 'File' element

        Returns:
          str: 'href' attribute value of this element
        """
        return file_obj.get(self.FILE_HREF)

    def get_file_ref_from_disk(self, disk):
        """Get the file reference from the given opaque disk object.

        Args:
          disk (xml.etree.ElementTree.Element): 'Disk' element

        Returns:
          str: 'fileRef' attribute value of this element
        """
        return disk.get(self.DISK_FILE_REF)

    def get_common_subtype(self, device_type):
        """Get the sub-type common to all devices of the given type.

        Args:
          device_type (str): Device type such as ``'ide'`` or ``'memory'``.

        Returns:
          str: Subtype string common to all devices of the type, or ``None``,
          if multiple such devices exist and they do not all have the same
          sub-type.
        """
        subtype = None
        for item in self.hardware.find_all_items(device_type):
            item_subtype = item.get_value(self.RESOURCE_SUB_TYPE)
            if subtype is None:
                subtype = item_subtype
                logger.verbose("Found %s subtype %s", device_type, subtype)
            elif subtype != item_subtype:
                logger.warning("Found different subtypes ('%s', '%s') for "
                               "device type %s - no common subtype exists",
                               subtype, item_subtype, device_type)
                return None
        return subtype

    def check_sanity_of_disk_device(self, disk, file_obj,
                                    disk_item, ctrl_item):
        """Check if the given disk is linked properly to the other objects.

        Args:
          disk (xml.etree.ElementTree.Element): Disk object to validate
          file_obj (xml.etree.ElementTree.Element): File object which this
              disk should be linked to (optional)
          disk_item (OVFItem): Disk device object which should link to this
              disk (optional)
          ctrl_item (OVFItem): Controller device object which should link
              to the :attr:`disk_item`

        Raises:
          ValueMismatchError: if the given items are not linked properly.
          ValueUnsupportedError: if the :attr:`disk_item` has a
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
                # TODO: this is not a user input error, it's an OVF error
                #       so ValueUnsupportedError isn't really right?
                raise ValueUnsupportedError("HostResource prefix",
                                            host_resource,
                                            [self.HOST_RSRC_FILE_REF,
                                             self.HOST_RSRC_DISK_REF,
                                             self.OLD_HOST_RSRC_FILE_REF,
                                             self.OLD_HOST_RSRC_DISK_REF])

    def add_file(self, file_path, file_id, file_obj=None, disk=None):
        """Add a new file object to the VM or overwrite the provided one.

        Args:
          file_path (str): Path to file to add
          file_id (str): Identifier string for the file in the VM
          file_obj (xml.etree.ElementTree.Element): Existing file object to
              overwrite
          disk (xml.etree.ElementTree.Element): Existing disk object
              referencing :attr:`file`.

        Returns:
          xml.etree.ElementTree.Element: New or updated file object
        """
        logger.debug("Adding File to OVF")

        if file_obj is not None:
            href = file_obj.get(self.FILE_HREF)
            if href in self.file_references.keys():
                del self.file_references[href]

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
        self.file_references[file_name] = FileReference.create(
            os.path.dirname(file_path), file_name,
            checksum_algorithm=self.checksum_algorithm)

        return file_obj

    def remove_file(self, file_obj, disk=None, disk_drive=None):
        """Remove the given file object from the VM.

        Args:
          file_obj (xml.etree.ElementTree.Element): File object to remove
          disk (xml.etree.ElementTree.Element): Disk object referencing
              :attr:`file`
          disk_drive (OVFItem): Disk drive mapping :attr:`file` to a device

        Raises:
          ValueUnsupportedError: If the ``disk_drive`` is a device type other
              than 'cdrom' or 'harddisk'
        """
        self.references.remove(file_obj)
        del self.file_references[file_obj.get(self.FILE_HREF)]

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

    def add_disk(self, disk_repr, file_id, drive_type, disk=None):
        """Add a new disk object to the VM or overwrite the provided one.

        Args:
          disk_repr (COT.disks.DiskRepresentation): Disk file representation
          file_id (str): Identifier string for the file/disk mapping
          drive_type (str): 'harddisk' or 'cdrom'
          disk (xml.etree.ElementTree.Element): Existing object to overwrite

        Returns:
          xml.etree.ElementTree.Element: New or updated disk object
        """
        if drive_type != 'harddisk':
            if disk is not None:
                logger.notice("CD-ROMs do not require a Disk element. "
                              "Existing element will be deleted.")
                if self.disk_section is not None:
                    self.disk_section.remove(disk)
                    if not self.disk_section.findall(self.DISK):
                        logger.notice("No Disks left - removing DiskSection")
                        self.envelope.remove(self.disk_section)
                        self.disk_section = None
                disk = None
            else:
                logger.debug("Not adding Disk element to OVF, as CD-ROMs "
                             "do not require a Disk")
            return disk

        # Else, adding a hard disk:
        self.disk_section = self._ensure_section(
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

        self.set_capacity_of_disk(disk, disk_repr.capacity)

        disk.set(self.DISK_ID, disk_id)
        disk.set(self.DISK_FILE_REF, file_id)
        disk.set(self.DISK_FORMAT,
                 ("http://www.vmware.com/interfaces/"
                  "specifications/vmdk.html#streamOptimized"))
        return disk

    def add_controller_device(self, device_type, subtype, address,
                              ctrl_item=None):
        """Create a new IDE or SCSI controller, or update existing one.

        Args:
          device_type (str): ``'ide'`` or ``'scsi'``
          subtype (object): (Optional) subtype string such as ``'virtio'``
              or list of subtype strings
          address (int): Controller address such as 0 or 1 (optional)
          ctrl_item (OVFItem): Existing controller device to update (optional)

        Returns:
          OVFItem: New or updated controller device object

        Raises:
          ValueTooHighError: if no more controllers can be created
        """
        if ctrl_item is None:
            logger.notice("%s controller not found, creating new Item",
                          device_type.upper())
            (_, ctrl_item) = self.hardware.new_item(device_type)
            if address is None:
                # Find a controller address that isn't already used
                address_list = [
                    ci.get_value(self.ADDRESS) for
                    ci in self.hardware.find_all_items(device_type)]
                address = 0
                while str(address) in address_list:
                    address += 1
                logger.verbose("Selected address %s for new controller",
                               address)
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

    def _create_new_disk_device(self, drive_type, address, name, ctrl_item):
        """Helper for :meth:`add_disk_device`, in the case of no prior Item.

        Args:
          drive_type (str): ``'harddisk'`` or ``'cdrom'``
          address (str): Address on controller, such as "1:0" (optional)
          name (str): Device name string (optional)
          ctrl_item (OVFItem): Controller object to serve as parent

        Returns:
          tuple: (disk_item, disk_name)

        Raises:
          ValueTooHighError: if the requested address is out of range
              for the given controller, or if the controller is already full.
          ValueUnsupportedError: if ``name`` is not specified and
              ``disk_type`` is not 'harddisk' or 'cdrom'.
        """
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

        ctrl_type = ctrl_item.hardware_type
        # Make sure the address is valid!
        if ctrl_type == "scsi" and int(address) > 15:
            raise ValueTooHighError("disk address on SCSI controller",
                                    address, 15)
        elif ctrl_type == "ide" and int(address) > 1:
            raise ValueTooHighError("disk address on IDE controller",
                                    address, 1)

        if name is None:
            if drive_type == 'cdrom':
                name = "CD-ROM Drive"
            elif drive_type == 'harddisk':
                name = "Hard Disk Drive"
            else:
                # Should never get here!
                raise ValueUnsupportedError("disk drive type", drive_type,
                                            "'cdrom' or 'harddisk'")

        (_, disk_item) = self.hardware.new_item(drive_type)
        disk_item.set_property(self.ADDRESS_ON_PARENT, address)
        disk_item.set_property(self.PARENT, ctrl_instance)

        return disk_item, name

    def add_disk_device(self, drive_type, address, name, description,
                        disk, file_obj, ctrl_item, disk_item=None):
        """Create a new disk hardware device or overwrite an existing one.

        Args:
          drive_type (str): ``'harddisk'`` or ``'cdrom'``
          address (str): Address on controller, such as "1:0" (optional)
          name (str): Device name string (optional)
          description (str): Description string (optional)
          disk (xml.etree.ElementTree.Element): Disk object to map to
              this device
          file_obj (xml.etree.ElementTree.Element): File object to map to
              this device
          ctrl_item (OVFItem): Controller object to serve as parent
          disk_item (OVFItem): Existing disk device to update instead of
              making a new device.

        Returns:
          xml.etree.ElementTree.Element: New or updated disk device object.
        """
        if disk_item is None:
            logger.notice("Disk Item not found, adding new Item")
            disk_item, name = self._create_new_disk_device(
                drive_type, address, name, ctrl_item)
        else:
            logger.debug("Updating existing disk Item")

        # Make these changes to the disk Item regardless of new/existing
        disk_item.set_property(self.RESOURCE_TYPE, self.RES_MAP[drive_type])
        if drive_type == 'harddisk':
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

        Args:
          file_path (str): OVA file path

        Returns:
          str: Path to extracted OVF descriptor

        Raises:
          VMInitError: if the given file doesn't represent a valid OVA archive.
        """
        logger.verbose("Untarring %s to working directory %s",
                       file_path, self.working_dir)

        try:
            tarf = tarfile.open(file_path, 'r')
        except (EOFError, tarfile.TarError) as exc:
            raise VMInitError(1, "Could not untar file: {0}".format(exc.args),
                              file_path)

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
                raise VMInitError(1, "No files to untar", file_path)
            # Make sure the provided file doesn't contain any malicious paths
            # http://stackoverflow.com/questions/8112742/
            for pathname in tarf.getnames():
                logger.debug("Examining path of %s prior to untar", pathname)
                if not (os.path.abspath(os.path.join(self.working_dir,
                                                     pathname))
                        .startswith(self.working_dir)):
                    raise VMInitError(1, "Tar file contains malicious/unsafe "
                                      "file path '{0}'!".format(pathname),
                                      file_path)

            ovf_descriptor = tarf.getmembers()[0]
            if os.path.splitext(ovf_descriptor.name)[1] != '.ovf':
                # Do we have an OVF descriptor elsewhere in the file?
                candidates = [mem for mem in tarf.getmembers() if
                              os.path.splitext(mem.name)[1] == '.ovf']
                if not candidates:
                    raise VMInitError(1,
                                      "TAR file does not seem to contain any"
                                      " .ovf file to serve as OVF descriptor"
                                      " - OVA is invalid!",
                                      file_path)
                ovf_descriptor = candidates[0]
                logger.error(
                    "OVF file %s found, but is not the first file in the TAR "
                    "as it should be - OVA is not standard-compliant!",
                    ovf_descriptor.name)

            # TODO: In theory we could read the ovf descriptor XML directly
            # from the TAR and not need to even extract this file to disk...
            tarf.extract(ovf_descriptor, path=self.working_dir)
            logger.debug(
                "Extracted OVF descriptor from %s to working dir %s",
                file_path, self.working_dir)
        finally:
            tarf.close()

        # Find the OVF file
        return os.path.join(self.working_dir, ovf_descriptor.name)

    def generate_manifest(self, ovf_file):
        """Construct the manifest file for this package, if possible.

        Args:
          ovf_file (str): OVF descriptor file path

        Returns:
          bool: True if the manifest was successfully generated,
          False if not successful (such as if checksum helper tools are
          unavailable).
        """
        (prefix, _) = os.path.splitext(ovf_file)
        logger.verbose("Generating manifest for %s", ovf_file)
        manifest = prefix + '.mf'
        with open(ovf_file, 'rb') as ovfobj:
            checksum = file_checksum(ovfobj, self.checksum_algorithm)
        with open(manifest, 'wb') as mfobj:
            mfobj.write("{algo}({file})= {sum}\n"
                        .format(algo=self.checksum_algorithm.upper(),
                                file=os.path.basename(ovf_file),
                                sum=checksum)
                        .encode('utf-8'))
            # Checksum all referenced files as well
            for file_obj in self.references.findall(self.FILE):
                file_name = file_obj.get(self.FILE_HREF)
                file_ref = self.file_references[file_name]

                mfobj.write("{algo}({file})= {sum}\n"
                            .format(algo=self.checksum_algorithm.upper(),
                                    file=file_name, sum=file_ref.checksum)
                            .encode('utf-8'))

        logger.debug("Manifest generated successfully")
        return True

    def tar(self, ovf_descriptor, tar_file):
        """Create a .ova tar file based on the given OVF descriptor.

        Args:
          ovf_descriptor (str): File path for an OVF descriptor
          tar_file (str): File path for the desired OVA archive.
        """
        logger.verbose("Creating tar file %s", tar_file)

        (prefix, _) = os.path.splitext(ovf_descriptor)

        # Issue #66 - need to detect any of the possible scenarios:
        # 1) output path and input path are the same real path
        #    (not just string-equal!)
        # 2) output file and input file are the same file (including links)
        # but not error out if (common case) output_file doesn't exist yet.
        if (os.path.realpath(self.input_file) == os.path.realpath(tar_file) or
            (os.path.exists(tar_file) and
             os.path.samefile(self.input_file, tar_file))):
            # We're about to overwrite the input OVA with a new OVA.
            # (Python tarfile module doesn't support in-place edits.)
            # Any files that we need to carry over need to be extracted NOW!
            logger.info(
                "Input OVA will be overwritten. Extracting files from %s to"
                " working directory before overwriting it.", self.input_file)
            for filename in self.file_references:
                file_ref = self.file_references[filename]
                if file_ref.file_path is None:
                    file_ref.copy_to(self.working_dir)
                    self.file_references[filename] = FileReference.create(
                        self.working_dir, filename,
                        checksum_algorithm=self.checksum_algorithm,
                        expected_checksum=file_ref.checksum,
                        expected_size=file_ref.size)

        # Be sure to dereference any links to the actual file content!
        with tarfile.open(tar_file, 'w', dereference=True) as tarf:
            # OVF is always first
            logger.debug("Adding OVF descriptor %s to %s",
                         ovf_descriptor, tar_file)
            tarf.add(ovf_descriptor, os.path.basename(ovf_descriptor))
            # Add manifest if present
            manifest_path = prefix + '.mf'
            if os.path.exists(manifest_path):
                logger.debug("Adding manifest to %s", tar_file)
                tarf.add(manifest_path, os.path.basename(manifest_path))
            if os.path.exists("{0}.cert".format(prefix)):
                logger.warning("COT doesn't know how to re-sign a certificate"
                               " file, so the existing certificate will be"
                               " omitted from %s.", tar_file)
            # Add all other files mentioned in the OVF
            for file_obj in self.references.findall(self.FILE):
                file_name = file_obj.get(self.FILE_HREF)
                file_ref = self.file_references[file_name]
                logger.debug("Adding associated file %s to %s",
                             file_name, tar_file)
                file_ref.add_to_archive(tarf)

    def _ensure_section(self, section_tag, info_string,
                        attrib=None, parent=None):
        """If the OVF doesn't already have the given Section, create it.

        Args:
          section_tag (str): XML tag of the desired section.
          info_string (str): Info string to set if a new Section is created.
          attrib (dict): Attributes to filter by when looking for any existing
              section (optional).
          parent (xml.etree.ElementTree.Element): Parent element (optional).
              If not specified, :attr:`envelope` will be the parent.

        Returns:
          xml.etree.ElementTree.Element: Section element that was found or
          created
        """
        if parent is None:
            parent = self.envelope
        section = self.find_child(parent, section_tag, attrib=attrib)
        if section is not None:
            return section

        logger.notice("No existing %s. Creating it.",
                      XML.strip_ns(section_tag))
        if attrib:
            section = ET.Element(section_tag, attrib=attrib)
        else:
            section = ET.Element(section_tag)
        # Section elements may be in arbitrary order relative to one another,
        # but they MUST come after the References and before the VirtualSystem.
        # We'll construct them immediately before the VirtualSystem.
        index = 0
        for child in list(parent):
            if child.tag == self.VIRTUAL_SYSTEM:
                break
            index += 1
        parent.insert(index, section)

        # All Sections must have an Info child
        self.set_or_make_child(section, self.INFO, info_string)

        return section

    def _set_product_section_child(self, child_tag, child_text):
        """Update or create the given child of the ProductSection.

        Creates the ProductSection itself if necessary.

        Args:
          child_tag (str): XML tag of the product section child element.
          child_text (str): Text to set for the child element.

        Returns:
          xml.etree.ElementTree.Element: The product section element that
          was updated or created
        """
        self.product_section = self._ensure_section(
            self.PRODUCT_SECTION,
            "Product Information",
            attrib=self.PRODUCT_SECTION_ATTRIB,
            parent=self.virtual_system)
        return self.set_or_make_child(self.product_section, child_tag,
                                      child_text)

    def find_parent_from_item(self, item):
        """Find the parent Item of the given Item.

        Args:
          item (OVFItem): Item whose parent is desired

        Returns:
          OVFItem: instance representing the parent device, or None
        """
        if item is None:
            return None

        parent_instance = item.get_value(self.PARENT)
        if parent_instance is None:
            logger.warning("Item instance %s has no 'Parent' subelement."
                           " Unable to identify parent Item.",
                           item.get_value(self.INSTANCE_ID))
            return None

        return self.hardware.find_item(
            properties={self.INSTANCE_ID: parent_instance})

    def find_item_from_disk(self, disk):
        """Find the disk Item that references the given Disk.

        Args:
          disk (xml.etree.ElementTree.Element): Disk element

        Returns:
          OVFItem: Corresponding instance, or None
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

        Args:
          file_obj (xml.etree.ElementTree.Element): File element

        Returns:
          OVFItem: Corresponding instance, or None.
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

        Args:
          file_id (str): File identifier string

        Returns:
          xml.etree.ElementTree.Element: Disk matching the file, or None
        """
        if file_id is None or self.disk_section is None:
            return None

        return self.find_child(self.disk_section, self.DISK,
                               attrib={self.DISK_FILE_REF: file_id})

    def find_empty_drive(self, drive_type):
        """Find a disk device that exists but contains no data.

        Args:
          drive_type (str): Either 'cdrom' or 'harddisk'

        Returns:
          OVFItem: Instance representing this disk device, or None.

        Raises:
          ValueUnsupportedError: if ``drive_type`` is unrecognized.
        """
        if drive_type == 'cdrom':
            # Find a drive that has no HostResource property
            drives = self.hardware.find_all_items(
                resource_type=drive_type,
                properties={self.HOST_RESOURCE: None})
            if drives:
                return drives[0]
            return None
        elif drive_type == 'harddisk':
            # All harddisk items must have a HostResource, so we need a
            # different way to indicate an empty drive. By convention,
            # we do this with a small placeholder disk (one with a Disk entry
            # but no corresponding File included in the OVF package).
            if self.disk_section is None:
                logger.debug("No DiskSection, so no placeholder disk!")
                return None
            for disk in self.disk_section.findall(self.DISK):
                file_id = disk.get(self.DISK_FILE_REF)
                if file_id is None:
                    # Found placeholder disk!
                    # Now find the drive that's using this disk.
                    return self.find_item_from_disk(disk)
            logger.debug("No placeholder disk found.")
            return None
        else:
            raise ValueUnsupportedError("drive type",
                                        drive_type,
                                        "'cdrom' or 'harddisk'")

    def find_device_location(self, device):
        """Find the controller type and address of a given device object.

        Args:
          device (OVFItem): Hardware device object.

        Returns:
          tuple: ``(type, address)``, such as ``("ide", "1:0")``.

        Raises:
          LookupError: if the controller is not found.
        """
        controller = self.find_parent_from_item(device)
        if controller is None:
            raise LookupError("No parent controller for device?")
        return (controller.hardware_type,
                (controller.get_value(self.ADDRESS) + ':' +
                 device.get_value(self.ADDRESS_ON_PARENT)))

    def get_id_from_disk(self, disk):
        """Get the identifier string associated with the given Disk object.

        Args:
          disk (xml.etree.ElementTree.Element): Disk object to inspect

        Returns:
          str: Disk identifier
        """
        return disk.get(self.DISK_ID)

    def get_capacity_from_disk(self, disk):
        """Get the capacity of the given Disk in bytes.

        Args:
          disk (xml.etree.ElementTree.Element): Disk element to inspect

        Returns:
          int: Disk capacity, in bytes
        """
        cap = int(disk.get(self.DISK_CAPACITY))
        cap_units = disk.get(self.DISK_CAP_UNITS, 'byte')
        return programmatic_bytes_to_int(cap, cap_units)

    def set_capacity_of_disk(self, disk, capacity_bytes):
        """Set the storage capacity of the given Disk.

        Tries to use the most human-readable form possible (i.e., 8 GiB
        instead of 8589934592 bytes).

        Args:
          disk (xml.etree.ElementTree.Element): Disk to update
          capacity_bytes (int): Disk capacity, in bytes
        """
        if self.ovf_version < 1.0:
            # In OVF 0.9 only bytes is supported as a unit
            disk.set(self.DISK_CAPACITY, capacity_bytes)
        else:
            (capacity, cap_units) = int_bytes_to_programmatic_units(
                capacity_bytes)
            disk.set(self.DISK_CAPACITY, capacity)
            disk.set(self.DISK_CAP_UNITS, cap_units)
