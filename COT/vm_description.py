#!/usr/bin/env python
#
# vm_description.py - Abstract class for reading, editing, and writing VMs
#
# September 2013, Glenn F. Matthews
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

"""Abstract superclass for reading, editing, and writing VMs.

.. autosummary::
  :nosignatures:

  VMInitError
  VMDescription
"""

import atexit
import logging
import os.path
import shutil
import tempfile

from verboselogs import VerboseLogger

from .data_validation import ValueUnsupportedError

logging.setLoggerClass(VerboseLogger)

logger = logging.getLogger(__name__)


class VMInitError(EnvironmentError):
    """Class representing errors encountered when trying to init/load a VM."""


class VMDescription(object):
    """Abstract class for reading, editing, and writing VM definitions.

    **Properties**

    .. autosummary::
      :nosignatures:

      input_file
      output_file
      platform
      config_profiles
      default_config_profile
      environment_properties
      networks
      system_types
      version_short
      version_long
    """

    @classmethod
    def detect_type_from_name(cls, filename):
        """Check the given filename to see if it looks like a type we support.

        Does not check file contents, as the given filename may not yet exist.

        :return: A string representing a recognized and supported type of file
        :raise ValueUnsupportedError: if we don't know how to handle this file.
        """
        raise ValueUnsupportedError("filename", filename, ("none implemented"))

    def __init__(self, input_file, output_file=None):
        """Read the given VM description file into memory.

        Also creates a temporary directory as a working directory.

        :param str input_file: Data file to read in.
        :param str output_file: File name to write to. If this VM is read-only,
          (there will never be an output file) this value should be ``None``;
          if the output filename is not yet known, use ``""`` and subsequently
          set :attr:`output` when it is determined.
        """
        self._input_file = input_file
        self.working_dir = tempfile.mkdtemp(prefix="cot")
        logger.verbose("Temporary directory for VM created from {0}: {1}"
                       .format(input_file, self.working_dir))
        self.output_file = output_file
        atexit.register(self.destroy)

    def destroy(self):
        """Clean up after ourselves.

        Deletes :attr:`self.working_dir` and its contents.
        """
        try:
            if hasattr(self,
                       'working_dir') and os.path.exists(self.working_dir):
                logger.debug("Removing temporary directory '{0}"
                             .format(self.working_dir))
                shutil.rmtree(self.working_dir)
        except AttributeError:
            pass

    def __del__(self):
        """Destructor. Call :meth:`destroy`."""
        self.destroy()

    @property
    def input_file(self):
        """Data file to read in."""
        return self._input_file

    @property
    def output_file(self):
        """Filename that :meth:`write` will output to."""
        return self._output_file

    @output_file.setter
    def output_file(self, value):
        self._output_file = value

    def write(self):
        """Write the VM description to :attr:`output_file`, if any."""
        raise NotImplementedError("write not implemented")

    @property
    def platform(self):
        """The Platform class object associated with this VM.

        :class:`~COT.platforms.GenericPlatform` or a more specific subclass
        if recognized as such.
        """
        raise NotImplementedError("no platform value available.")

    @property
    def config_profiles(self):
        """The list of supported configuration profiles.

        If there are no profiles defined, returns an empty list.
        If there is a default profile, it will be first in the list.
        """
        raise NotImplementedError("config_profiles not implemented!")

    @property
    def default_config_profile(self):
        """The name of the default configuration profile.

        :return: Profile name or ``None`` if none are defined.
        """
        if self.config_profiles:
            return self.config_profiles[0]
        return None

    @property
    def environment_properties(self):
        """The array of environment properties.

        :return: Array of dicts (one per property) with the keys
          ``"key"``, ``"value"``, ``"qualifiers"``, ``"type"``,
          ``"label"``, and ``"description"``.
        """
        raise NotImplementedError("environment_properties not implemented")

    @property
    def networks(self):
        """The list of network names currently defined in this VM.

        :rtype: list[str]
        """
        raise NotImplementedError("networks property not implemented!")

    @property
    def system_types(self):
        """List of virtual system type(s) supported by this virtual machine."""
        raise NotImplementedError("system_types not implemented!")

    @system_types.setter
    def system_types(self, type_list):
        raise NotImplementedError("system_types setter not implemented!")

    @property
    def version_short(self):
        """A short string describing the product version."""
        raise NotImplementedError("version_short not implemented!")

    @version_short.setter
    def version_short(self, value):
        raise NotImplementedError("version_short setter not implemented!")

    @property
    def version_long(self):
        """A long string describing the product version."""
        raise NotImplementedError("version_long not implemented!")

    @version_long.setter
    def version_long(self, value):
        raise NotImplementedError("version_long setter not implemented")

    # API methods needed for add-disk
    def convert_disk_if_needed(self, file_path, kind):
        """Convert the disk to a more appropriate format if needed.

        :param str file_path: Image to inspect and possibly convert
        :param str kind: Image type (harddisk/cdrom)
        :return:
          * :attr:`file_path`, if no conversion was required
          * or a file path in :attr:`output_dir` containing the converted image
        """
        # Some VMs may not need this, so default to do nothing, not error
        return file_path

    def search_from_filename(self, filename):
        """From the given filename, try to find any existing objects.

        :param str filename: Filename to search from
        :return: ``(file, disk, controller_device, disk_device)``,
          opaque objects of which any or all may be ``None``
        """
        raise NotImplementedError("search_from_filename not implemented")

    def search_from_file_id(self, file_id):
        """From the given file ID, try to find any existing objects.

        :param str filename: Filename to search from
        :return: ``(file, disk, controller_device, disk_device)``,
          opaque objects of which any or all may be ``None``
        """
        raise NotImplementedError("search_from_file_id not implemented")

    def search_from_controller(self, controller, address):
        """From the controller type and device address, look for existing disk.

        :param str controller: ``'ide'`` or ``'scsi'``
        :param str address: Device address such as ``'1:0'``
        :return: ``(file, disk, controller_device, disk_device)``,
          opaque objects of which any or all may be ``None``
        """
        raise NotImplementedError("search_from_controller not implemented")

    def find_open_controller(self, type):
        """Find the first open slot on a controller of the given type.

        :param str type: ``'ide'`` or ``'scsi'``
        :return: ``(controller_device, address_string)`` or ``(None, None)``
        """
        raise NotImplementedError("find_open_controller not implemented")

    def get_id_from_file(self, file):
        """Get the file ID from the given opaque file object.

        :param file: File object to query
        :return: Identifier string associated with this object
        """
        raise NotImplementedError("get_id_from_file not implemented")

    def get_path_from_file(self, file):
        """Get the file path from the given opaque file object.

        :param file: File object to query
        :return: Relative path to the file associated with this object
        """
        raise NotImplementedError("get_path_from_file not implemented")

    def get_file_ref_from_disk(self, disk):
        """Get the file reference from the given opaque disk object.

        :param disk: Disk object to query
        :return: String that can be used to identify the file associated
          with this disk
        """
        raise NotImplementedError("get_file_ref_from_disk not implemented")

    def get_type_from_device(self, device):
        """Get the type of the given opaque device object.

        :param device: Device object to query
        :return: string such as 'ide' or 'memory'
        """
        raise NotImplementedError("get_type_from_device not implemented")

    def get_subtype_from_device(self, device):
        """Get the sub-type of the given opaque device object.

        :param device: Device object to query
        :return: ``None``, or string such as 'virtio' or 'lsilogic'
        """
        raise NotImplementedError("get_subtype_from_device not implemented")

    def get_common_subtype(self, type):
        """Get the sub-type common to all devices of the given type.

        :param str type: Device type such as ``'ide'`` or ``'memory'``.
        :return: ``None``, if multiple such devices exist and they do not all
          have the same sub-type.
        :return: Subtype string common to all devices of the type.
        """
        raise NotImplementedError("get_common_subtype not implemented")

    def check_sanity_of_disk_device(self, disk, file, disk_item, ctrl_item):
        """Check if the given disk is linked properly to the other objects.

        :param disk: Disk object to validate
        :param file: File object which this disk should be linked to (optional)
        :param disk_item: Disk device object which should link to this disk
          (optional)
        :param ctrl_item: Controller device object which should link to the
          :attr:`disk_item`
        :raise ValueMismatchError: if the given items are not linked properly.
        """
        raise NotImplementedError(
            "check_sanity_of_disk_device not implemented")

    def add_file(self, file_path, file_id, file=None, disk=None):
        """Add a new file object to the VM or overwrite the provided one.

        :param str file_path: Path to file to add
        :param str file_id: Identifier string for the file in the VM
        :param file: Existing file object to overwrite
        :param disk: Existing disk object referencing :attr:`file`.

        :return: New or updated file object
        """
        raise NotImplementedError("add_file not implemented")

    def add_disk(self, file_path, file_id, disk_type, disk=None):
        """Add a new disk object to the VM or overwrite the provided one.

        :param str file_path: Path to disk image file
        :param str file_id: Identifier string for the file/disk mapping
        :param str disk_type: 'harddisk' or 'cdrom'
        :param disk: Existing disk object to overwrite

        :return: New or updated disk object
        """
        raise NotImplementedError("add_disk not implemented")

    def add_controller_device(self, type, subtype, address, ctrl_item=None):
        """Create a new IDE or SCSI controller, or update existing one.

        :param str type: ``'ide'`` or ``'scsi'``
        :param str subtype: Subtype such as ``'virtio'`` (optional)
        :param int address: Controller address such as 0 or 1 (optional)
        :param ctrl_item: Existing controller device to update (optional)

        :return: New or updated controller device object
        """
        raise NotImplementedError("add_controller_device not implemented")

    def add_disk_device(self, type, address, name, description, disk, file,
                        ctrl_item, disk_item=None):
        """Add a new disk device to the VM or update the provided one.

        :param str type: ``'harddisk'`` or ``'cdrom'``
        :param str address: Address on controller, such as "1:0" (optional)
        :param str name: Device name string (optional)
        :param str description: Description string (optional)
        :param disk: Disk object to map to this device
        :param file: File object to map to this device
        :param ctrl_item: Controller object to serve as parent
        :param disk_item: Existing disk device to update instead of making
          a new device.

        :return: New or updated disk device object.
        """
        raise NotImplementedError("add_disk_device not implemented")

    # API methods needed for edit-hardware
    def create_configuration_profile(self, id, label, description):
        """Create/update a configuration profile with the given ID.

        :param id: Profile identifier
        :param str label: Brief descriptive label for the profile
        :param str description: Verbose description of the profile
        """
        raise NotImplementedError("create_configuration_profile "
                                  "not implemented!")

    def delete_configuration_profile(self, profile):
        """Delete the configuration profile with the given ID."""
        raise NotImplementedError("delete_configuration_profile "
                                  "not implemented")

    # A note on getters/setters that take a profile_list parameter:
    #
    # A profile name of None is taken to mean "the default for all profiles
    # now or in the future that do not explicitly have a different value set."
    #
    # A profile_list of None or [] is taken to mean "all profiles, including
    # the default, as well as any to be defined in the future". For a VM with
    # profiles 'a' and 'b' currently defined, this is equivalent to the list
    # [None, 'a', 'b']
    #
    # A profile_list of [None] means "the default value to be inherited by
    # any other profiles that do not override it"
    #
    # A profile_list of [None, "a"] means "the default and profile 'a'". For a
    # setter function, this translates to "change 'a' to inherit the default,
    # and change the default as well."
    #
    # A profile_list of ["a", "b", "c"] means "profiles 'a', 'b', and 'c', but
    # not the default.

    def set_cpu_count(self, cpus, profile_list):
        """Set the number of CPUs.

        :param int cpus: Number of CPUs
        :param list profile_list: Change only the given profiles
        """
        raise NotImplementedError("set_cpu_count not implemented!")

    def set_memory(self, megabytes, profile_list):
        """Set the amount of RAM, in megabytes.

        :param int megabytes: Memory value, in megabytes
        :param list profile_list: Change only the given profiles
        """
        raise NotImplementedError("set_memory not implemented!")

    def set_nic_type(self, type, profile_list):
        """Set the hardware type for NICs.

        :param str type: NIC hardware type
        :param list profile_list: Change only the given profiles.
        """
        raise NotImplementedError("set_nic_type not implemented!")

    def get_nic_count(self, profile_list):
        """Get the number of NICs under the given profile(s).

        :param list profile_list: Profile(s) of interest.
        :rtype: dict
        :return: ``{ profile_name : nic_count }``
        """
        raise NotImplementedError("get_nic_count not implemented!")

    def set_nic_count(self, count, profile_list):
        """Set the given profile(s) to have the given number of NICs.

        :param int count: number of NICs
        :param list profile_list: Change only the given profiles
        """
        raise NotImplementedError("set_nic_count not implemented!")

    def create_network(self, label, description):
        """Define a new network with the given label and description.

        :param str label: Brief label for the network
        :param str description: Verbose description of the network
        """
        raise NotImplementedError("create_network not implemented!")

    def set_nic_networks(self, network_list, profile_list):
        """Set the NIC to network mapping for NICs under the given profile(s).

        .. note::
          If the length of :attr:`network_list` is less than the number of
          NICs, will use the last entry in the list for all remaining NICs.

        :param list network_list: List of networks to map NICs to
        :param list profile_list: Change only the given profiles
        """
        raise NotImplementedError("set_nic_networks not implemented!")

    def set_nic_mac_addresses(self, mac_list, profile_list):
        """Set the MAC addresses for NICs under the given profile(s).

        .. note::
          If the length of :attr:`mac_list` is less than the number of NICs,
          will use the last entry in the list for all remaining NICs.

        :param list mac_list: List of MAC addresses to assign to NICs
        :param list profile_list: Change only the given profiles
        """
        raise NotImplementedError("set_nic_mac_addresses not implemented!")

    def set_nic_names(self, name_list, profile_list):
        """Set the device names for NICs under the given profile(s).

        Since NICs are often named sequentially, this API supports a wildcard
        option for the final element in :attr:`name_list` which can be
        expanded to automatically assign sequential NIC names.
        The syntax for the wildcard option is ``{`` followed by a number
        (indicating the starting index for the name) followed by ``}``.
        Examples:

        ``["eth{0}"]``
          Expands to ``["eth0", "eth1", "eth2", ...]``
        ``["mgmt0" "eth{10}"]``
          Expands to ``["mgmt0", "eth10", "eth11", "eth12", ...]``

        :param list name_list: List of names to assign.
        :param list profile_list: Change only the given profiles
        """
        raise NotImplementedError("set_nic_names not implemented!")

    def get_serial_count(self, profile_list):
        """Get the number of serial ports under the given profile(s).

        :rtype: dict
        :return: ``{ profile_name : serial_count }``
        """
        raise NotImplementedError("get_serial_count not implemented!")

    def set_serial_count(self, count, profile_list):
        """Set the given profile(s) to have the given number of NICs.

        :param int count: Number of serial ports
        :param list profile_list: Change only the given profiles
        """
        raise NotImplementedError("set_serial_count not implemented!")

    def set_serial_connectivity(self, conn_list, profile_list):
        """Set the serial port connectivity under the given profile(s).

        :param list conn_list: List of connectivity strings
        :param list profile_list: Change only the given profiles
        """
        raise NotImplementedError("set_serial_connectivity not implemented!")

    def get_serial_connectivity(self, profile):
        """Get the serial port connectivity strings under the given profile.

        :param str profile: Profile of interest.
        :return: List of connectivity strings
        """
        raise NotImplementedError("get_serial_connectivity not implemented!")

    def set_scsi_subtype(self, type, profile_list):
        """Set the device subtype for the SCSI controller(s).

        :param str type: SCSI subtype string
        :param list profile_list: Change only the given profiles
        """
        raise NotImplementedError("set_scsi_subtype not implemented!")

    def set_ide_subtype(self, type, profile_list):
        """Set the device subtype for the IDE controller(s).

        :param str type: IDE subtype string
        :param list profile_list: Change only the given profiles
        """
        raise NotImplementedError("set_ide_subtype not implemented!")

    # API methods needed for edit-product
    # API methods needed for edit-properties
    def get_property_value(self, key):
        """Get the value of the given property.

        :param str key: Property identifier
        :return: Value of this property, or ``None``
        """
        raise NotImplementedError("get_property_value not implemented")

    def set_property_value(self, key, value):
        """Set the value of the given property (converting value if needed).

        :param str key: Property identifier
        :param value: Value to set for this property
        :return: the (converted) value that was set.
        """
        raise NotImplementedError("set_property_value not implemented")

    def config_file_to_properties(self, file):
        """Import each line of a text file into a configuration property.

        :param str file: File name to import.
        """
        raise NotImplementedError("config_file_to_properties not implemented")

    # API methods needed for info
    verbosity_options = {
        'brief': 0,
        None: 1,
        'verbose': 2
        }

    def info_string(self, width=79, verbosity_option=None):
        """Get a descriptive string summarizing the contents of this VM.

        :param int width: Line length to wrap to where possible.
        :param str verbosity_option: ``'brief'``, ``None`` (default),
          or ``'verbose'``

        :return: Wrapped, appropriately verbose string.
        """
        raise NotImplementedError("info_string not implemented")

    def profile_info_string(self, width=79, verbosity_option=None,
                            enumerate=False):
        """Get a string summarizing available configuration profiles.

        :param int TEXT_WIDTH: Line length to wrap to if possible
        :param str verbosity_option: ``'brief'``, ``None`` (default),
          or ``'verbose'``

        :param boolean enumerate: If ``True``, number the profiles.
        :return: Appropriately formatted and verbose string.
        """
        raise NotImplementedError("profile_info_string not implemented")

    # API methods needed for inject-config
    def find_empty_drive(self, type):
        """Find a disk device that exists but contains no data.

        :param str type: Disk type, such as 'cdrom' or 'harddisk'
        :return: Hardware device object, or None.
        """
        raise NotImplementedError("find_empty_drive not implemented")

    def find_device_location(self, device):
        """Find the controller type and address of a given device object.

        :param device: Hardware device object.
        :returns: ``(type, address)``, such as ``("ide", "1:0")``.
        """
        raise NotImplementedError("find_device_location not implemented")
