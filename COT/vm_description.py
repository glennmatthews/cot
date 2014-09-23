#!/usr/bin/env python
#
# vm_description.py - Abstract class for reading, editing, and writing VMs
#
# September 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

class VMInitError(EnvironmentError):
    """Class representing errors encountered when trying to init/load a VM.
    """


class VMDescription(object):
    """Abstract class for reading, editing, and writing VMs"""

    @classmethod
    def detect_type_from_name(cls, filename):
        """Checks the given filename (not file contents, as filename may not
        exist yet) to see whether it appears to describe a file type supported
        by this VM class.
        Returns a string representing the type of this file,
        or raises a ValueUnsupportedError otherwise.
        """
        raise NotImplementedError("detect_type_from_name not implemented")

    def __init__(self, input_file, working_dir, output_file):
        """Read the given VM description file into memory and
        make note of the requested working directory and eventual output file"""
        self.input_file = input_file
        self.working_dir = working_dir
        self.output_file = output_file

    def write(self):
        """Write the VM description to the previously specified output file"""
        raise NotImplementedError("write not implemented")

    def get_platform(self):
        """Returns the Platform class object described by this VM description"""
        raise NotImplementedError("get_platform not implemented")

    def validate_file_references(self):
        """Check whether all files referenced by this VM description exist and
        are correctly described.
        Returns True (all files valid) or False (one or more missing/invalid).
        """
        raise NotImplementedError("validate_file_references not implemented")

    # API methods needed for add-disk
    def convert_disk_if_needed(self, filename, kind):
        """Converts the disk to a new format (and returns the path to the new
        disk), if appropriate"""
        # Some VMs may not need this, so do nothing by default rather than error
        return filename

    def search_from_filename(self, filename):
        """Use the provided filename to check for existing disks.
        Returns the opaque objects (file, disk, controller_device, disk_device)
        """
        raise NotImplementedError("search_from_filename not implemented")

    def search_from_file_id(self, file_id):
        """Use the provided file ID to check for existing disks.
        Returns the opaque objects (file, disk, controller_device, disk_device)
        """
        raise NotImplementedError("search_from_file_id not implemented")

    def search_from_controller(self, controller, address):
        """Use the provided controller and address (such as 'ide', '1:0')
        to check for existing disks.
        Returns the opaque objects (file, disk, controller_device, disk_device)
        """
        raise NotImplementedError("search_from_controller not implemented")

    def find_open_controller(self, type):
        """Find the first open slot on a controller of the given type.
        Returns (controller_device, address)"""
        raise NotImplementedError("find_open_controller not implemented")

    def get_id_from_file(self, file):
        """Get the file ID from the given opaque file object"""
        raise NotImplementedError("get_id_from_file not implemented")

    def get_path_from_file(self, file):
        """Get the file path from the given opaque file object"""
        raise NotImplementedError("get_path_from_file not implemented")

    def get_file_ref_from_disk(self, disk):
        """Get the file reference from the given opaque disk object"""
        raise NotImplementedError("get_file_ref_from_disk not implemented")

    def get_type_from_device(self, device):
        """Get the major type of the given opaque device object"""
        raise NotImplementedError("get_type_from_device not implemented")

    def get_subtype_from_device(self, device):
        """Get the sub-type of the given opaque device object"""
        raise NotImplementedError("get_subtype_from_device not implemented")

    def get_common_subtype(self, type):
        """Get the sub-type common to all devices of the given type. If
        multiple such devices exist and they do not all have the same sub-type,
        returns None."""
        raise NotImplementedError("get_common_subtype not implemented")

    def check_sanity_of_disk_device(self, disk, file, disk_item, ctrl_item):
        """Make sure the indicated disk device has appropriate linkage to any
        disk, file, and controller provided. Die if it does not."""
        raise NotImplementedError("check_sanity_of_disk_device not implemented")

    def add_file(self, file_path, file_id, file=None, disk=None):
        """Add a new file object to the VM or overwrite the provided one"""
        raise NotImplementedError("add_file not implemented")

    def add_disk(self, file_path, file_id, disk_type, disk=None):
        """Add a new disk object to the VM or update the provided one"""
        raise NotImplementedError("add_disk not implemented")

    def add_controller_device(self, type, subtype, address, ctrl_item=None):
        """Add a new controller device to the VM or update the provided one"""
        raise NotImplementedError("add_controller_device not implemented")

    def add_disk_device(self, type, address, name, description, disk, file,
                        ctrl_item, disk_item=None):
        """Add a new disk device to the VM or update the provided one"""
        raise NotImplementedError("add_disk_device not implemented")

    # API methods needed for edit-hardware
    def get_configuration_profile_ids(self):
        """Return a list of named configuration profiles in the VM.
        If there are no profiles defined, returns an empty list.
        """
        raise NotImplementedError("get_configuration_profile_ids "
                                  "not implemented!")

    def create_configuration_profile(self, id, label, description):
        """Create/update a configuration profile with the given ID"""
        raise NotImplementedError("create_configuration_profile "
                                  "not implemented!")

    def set_system_type(self, type_list):
        """Set the virtual system type(s) supported by this virtual machine."""
        raise NotImplementedError("set_system_type not implemented!")

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
        raise NotImplementedError("set_cpu_count not implemented!")

    def set_memory(self, megabytes, profile_list):
        raise NotImplementedError("set_memory not implemented!")

    def set_nic_type(self, type, profile_list):
        raise NotImplementedError("set_nic_type not implemented!")

    def get_nic_count(self, profile_list):
        """Get the number of NICs under the given profile(s).
        Returns a dictionary of profile_name:nic_count.
        """
        raise NotImplementedError("get_nic_count not implemented!")

    def set_nic_count(self, count, profile_list):
        """Set the given profile(s) to have the given number of NICs.
        """
        raise NotImplementedError("set_nic_count not implemented!")

    def get_network_list(self):
        """Gets the list of network names currently defined in this VM.
        """
        raise NotImplementedError("get_network_list not implemented!")

    def create_network(self, label, description):
        """Define a new network with the given label and description.
        """
        raise NotImplementedError("create_network not implemented!")

    def set_nic_networks(self, network_list, profile_list):
        """Set the NIC to network mapping for NICs under the given profile(s).
        """
        raise NotImplementedError("set_nic_networks not implemented!")

    def set_nic_mac_addresses(self, mac_list, profile_list):
        """Set the MAC addresses for NICs under the given profile(s).
        """
        raise NotImplementedError("set_nic_mac_addresses not implemented!")

    def get_serial_count(self, profile_list):
        """Get the number of serial ports under the given profile(s).
        Returns a dictionary of profile_name:serial_count.
        """
        raise NotImplementedError("get_serial_count not implemented!")

    def set_serial_count(self, count, profile_list):
        """Set the given profile(s) to have the given number of NICs.
        """
        raise NotImplementedError("set_serial_count not implemented!")

    def set_serial_connectivity(self, conn_list, profile_list):
        """Set the serial port connectivity under the given profile(s).
        """
        raise NotImplementedError("set_serial_connectivity not implemented!")

    def set_scsi_subtype(self, type, profile_list):
        raise NotImplementedError("set_scsi_subtype not implemented!")

    def set_ide_subtype(self, type, profile_list):
        raise NotImplementedError("set_ide_subtype not implemented!")

    # API methods needed for edit-product
    def set_short_version(self, version_string):
        raise NotImplementedError("set_version not implemented!")

    def set_long_version(self, version_string):
        raise NotImplementedError("set_version not implemented")

    # API methods needed for edit-properties
    def get_property_keys(self):
        """Get a list of property keys"""
        raise NotImplementedError("get_property_keys not implemented")

    def get_property_value(self, key):
        """Get the value of the given property, or None
        """
        raise NotImplementedError("get_property_value not implemented")

    def set_property_value(self, key, value):
        """Set the value of the given property (converting the value if needed).
        Returns the value that was set.
        """
        raise NotImplementedError("set_property_value not implemented")

    def get_property_qualifiers(self, key):
        """Get the list of qualifiers applicable to the given key
        """
        raise NotImplementedError("get_property_qualifiers not implemented")

    def get_property_type(self, key):
        """Get the type (string/boolean) applicable to the given key
        """
        raise NotImplementedError("get_property_type not implemented")

    def get_property_label(self, key):
        """Get the descriptive label corresponding to the given key
        """
        raise NotImplementedError("get_property_label not implemented")

    def get_property_description(self, key):
        """Get the detailed description corresponding to the given key
        """
        raise NotImplementedError("get_property_description not implemented")

    def config_file_to_properties(self, file):
        """Import each line of the provided file into a configuration property
        """
        raise NotImplementedError("config_file_to_properties not implemented")

    # API methods needed for info
    verbosity_options = {
        'brief': 0,
        None: 1,
        'verbose': 2
        }
    def info_string(self, verbosity_option=None):
        """Returns a descriptive string summarizing the contents of this VM
        """
        raise NotImplementedError("info_string not implemented")

    def profile_info_string(self):
        """Returns a descriptive string summarizing the different configuration
           profiles of this VM."""
        raise NotImplementedError("profile_info_string not implemented")

    def get_default_profile_name(self):
        """Returns the name of the default configuration profile for the VM
        """
        raise NotImplementedError("get_default_profile_name not implemented")

    # API methods needed for inject-config
    def find_empty_drive(self, type):
        """Returns a disk device (if any) of the requested type
        that exists but contains no data.
        """
        raise NotImplementedError("find_empty_drive not implemented")

    def find_device_location(self, device):
        """Returns the tuple (type, address), such as ("ide", "1:0")
        associated with the given device.
        """
        raise NotImplementedError("find_device_location not implemented")
