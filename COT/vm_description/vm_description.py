#!/usr/bin/env python
#
# vm_description.py - Abstract class for reading, editing, and writing VMs
#
# September 2013, Glenn F. Matthews
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

"""Abstract superclass for reading, editing, and writing VMs.

.. autosummary::
  :nosignatures:

  VMInitError
  VMDescription
"""

from __future__ import print_function

import atexit
import logging
import os
import os.path
import shutil
import tempfile
import warnings

from COT.data_validation import ValueUnsupportedError
from COT.utilities import directory_size, pretty_bytes

logger = logging.getLogger(__name__)


class VMInitError(EnvironmentError):
    """Class representing errors encountered when trying to init/load a VM."""


class VMDescription(object):
    """Abstract class for reading, editing, and writing VM definitions.

    Examples:
      Because instantiating this class creates a temporary directory
      (:attr:`working_dir`), it's important to always clean up.
      This can be done explicitly::

        >>> foo = VMDescription("foo.txt", None)
        >>> tmpdir = foo.working_dir
        >>> os.path.exists(tmpdir)
        True
        >>> foo.destroy()
        >>> os.path.exists(tmpdir)
        False

      or implicitly by using this class as a context manager::

        >>> with VMDescription("foo.txt", None) as foo:
        ...     tmpdir = foo.working_dir
        ...     os.path.exists(tmpdir)
        ...
        True
        >>> os.path.exists(tmpdir)
        False

      If the specific VM class is unknown, you can use the
      :meth:`factory` method to try to obtain an appropriate subclass::

        >>> try:    # doctest: +ELLIPSIS
        ...     with VMDescription.factory("foo.txt", None) as foo:
        ...         print(foo.__class__.__name__)
        ... except VMInitError as e:
        ...     print(e)
        [Errno 2] Unknown VM description type for input file...


    **Properties**

    .. autosummary::
      :nosignatures:

      input_file
      output_file
      working_dir
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

    # Many of these methods are abstract interfaces, so quiet, Pylint!
    # pylint: disable=missing-raises-doc
    # pylint: disable=redundant-returns-doc
    # pylint: disable=no-self-use, unused-argument

    @classmethod
    def detect_type_from_name(cls, filename):
        """Check the given filename to see if it looks like a type we support.

        Does not check file contents, as the given filename may not yet exist.

        Args:
          filename (str): File name or path
        Returns:
          str: A string representing a recognized and supported type of file
        Raises:
          ValueUnsupportedError: if COT can't recognize the file type or
              doesn't know how to handle this file type.
        """
        raise ValueUnsupportedError("filename", filename, ("none implemented"))

    @classmethod
    def factory(cls, input_file, *args, **kwargs):
        """Factory method to select and create the appropriate subclass.

        Args:
          input_file (str): Input file to test against each class's
            :meth:`detect_type_from_name` implementation.
          *args: Passed through to selected subclass :meth:`__init__`.
          **kwargs: Passed through to selected subclass :meth:`__init__`.

        Returns:
          VMDescription: appropriate subclass instance.

        Raises:
          VMInitError: if no appropriate subclass is identified
          VMInitError: if the selected subclass fails instantiation
        """
        vm_class = None
        supported_types = []
        # pylint doesn't know about __subclasses__
        # https://github.com/PyCQA/pylint/issues/555
        # TODO: this should be fixed when pylint 2.0 is released
        # pylint:disable=no-member
        for candidate_class in VMDescription.__subclasses__():
            try:
                candidate_class.detect_type_from_name(input_file)
                vm_class = candidate_class
                break
            except ValueUnsupportedError as exc:
                supported_types += [exc.expected_value]

        if not vm_class:
            raise VMInitError(2,
                              "Unknown VM description type for input file -"
                              " only supported types are {0}"
                              .format(supported_types),
                              input_file)

        logger.info("Loading '%s' as %s", input_file, vm_class.__name__)
        try:
            vm = vm_class(input_file, *args, **kwargs)
        except ValueUnsupportedError as exc:
            raise VMInitError(2, str(exc), input_file)
        logger.info("Successfully loaded %s from %s",
                    vm_class.__name__, input_file)

        return vm

    def __init__(self, input_file, output_file=None):
        """Read the given VM description file into memory.

        Also creates a temporary directory as a working directory.

        Args:
          input_file (str): Data file to read in.
          output_file (str): File name to write to.

              * If this VM is read-only, (there will never be an output file)
                this value should be ``None``
              * If the output filename is not yet known, use ``""`` and
                subsequently set :attr:`output` when it is determined.
        """
        self._input_file = input_file
        self._product_class = None
        logger.verbose("Creating temporary working directory for this VM")
        self._working_dir = tempfile.mkdtemp(prefix="cot")
        logger.debug("Working directory: %s", self.working_dir)
        self._output_file = None
        self.output_file = output_file
        atexit.register(self.destroy)

    def __enter__(self):
        """Begin a block using this VM as a context manager object."""
        return self

    def __exit__(self, exc_type, exc_value, trace):
        """Exiting context manager block. If no error, call :meth:`write`.

        In any case, also call :meth:`destroy`.
        For the parameters, see :mod:`contextlib`.
        """
        try:
            if exc_type is None:
                self.write()
        finally:
            self.destroy()

    def destroy(self):
        """Clean up after ourselves.

        Deletes :attr:`self.working_dir` and its contents.
        """
        try:
            if hasattr(self,
                       'working_dir') and os.path.exists(self.working_dir):
                logger.verbose("Removing working directory")
                total_size = directory_size(self.working_dir)
                logger.debug("Size of working directory '%s', prior to"
                             " removal, is %s",
                             self.working_dir,
                             pretty_bytes(total_size))
                # Clean up
                shutil.rmtree(self.working_dir)
        except AttributeError:
            pass

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

    @property
    def working_dir(self):
        """Temporary directory this instance can use for storage.

        Will be automatically erased when :meth:`destroy` is called.
        """
        return self._working_dir

    def write(self):
        """Write the VM description to :attr:`output_file`, if any."""
        if self.output_file:
            raise NotImplementedError("write not implemented")

    @property
    def product_class(self):
        """The product class identifier, such as com.cisco.csr1000v."""
        return self._product_class

    @product_class.setter
    def product_class(self, product_class):
        self._product_class = product_class

    @property
    def platform(self):
        """The Platform instance object associated with this VM.

        An instance of :class:`~COT.platforms.Platform` or a more specific
        subclass if recognized as such.
        """
        raise NotImplementedError("no platform value available.")

    def validate_hardware(self):
        """Check sanity of hardware properties for this VM/product/platform.

        Returns:
          bool: ``True`` if hardware is sane, ``False`` if not.
        """
        raise NotImplementedError("validate_hardware not implemented!")

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

        Returns:
          str: Profile name or ``None`` if none are defined.
        """
        if self.config_profiles:
            return self.config_profiles[0]
        return None

    @property
    def environment_properties(self):
        """The array of environment properties.

        Returns:
          list: Array of dicts (one per property) with the keys
          ``"key"``, ``"value"``, ``"qualifiers"``, ``"type"``,
          ``"label"``, and ``"description"``.
        """
        raise NotImplementedError("environment_properties not implemented")

    @property
    def environment_transports(self):
        """The list of environment transport methods."""
        raise NotImplementedError("environment_transports not implemented")

    @environment_transports.setter
    def environment_transports(self, value):
        raise NotImplementedError("environment_transports not implemented")

    @property
    def networks(self):
        """The list of network names currently defined in this VM."""
        raise NotImplementedError("networks property not implemented!")

    @property
    def network_descriptions(self):
        """The list of network descriptions currently defined in this VM."""
        raise NotImplementedError(
            "network_descriptions property not implemented!")

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

    def predicted_output_size(self):
        """Estimate how much disk space (in bytes) is needed to write out.

        Returns:
          int: Estimated number of bytes consumed when writing out to
            :attr:`output_file` (plus any associated files).
        """
        raise NotImplementedError("predicted_output_size not implemented")

    # API methods needed for add-disk
    def convert_disk_if_needed(self,   # pylint: disable=no-self-use
                               disk_image,
                               kind):  # pylint: disable=unused-argument
        """Convert the disk to a more appropriate format if needed.

        Args:
          disk_image (DiskRepresentation): Disk to inspect and possibly convert
          kind (str): Image type (harddisk/cdrom).
        Returns:
          DiskRepresentation: :attr:`disk_image`, if no conversion was
          required, or a new :class:`~COT.disks.disk.DiskRepresentation`
          instance representing a converted image that has been created in
          :attr:`output_dir`.
        """
        # Some VMs may not need this, so default to do nothing, not error
        return disk_image

    def search_from_filename(self, filename):
        """From the given filename, try to find any existing objects.

        Args:
          filename (str): Filename to search from
        Returns:
          tuple: ``(file, disk, controller_device, disk_device)``, opaque
          objects of which any or all may be ``None``
        """
        raise NotImplementedError("search_from_filename not implemented")

    def search_from_file_id(self, file_id):
        """From the given file ID, try to find any existing objects.

        Args:
          file_id (str): File ID to search from
        Returns:
          tuple: ``(file, disk, controller_device, disk_device)``, opaque
          objects of which any or all may be ``None``
        """
        raise NotImplementedError("search_from_file_id not implemented")

    def search_from_controller(self, controller, address):
        """From the controller type and device address, look for existing disk.

        Args:
          controller (str): ``'ide'`` or ``'scsi'``
          address (str): Device address such as ``'1:0'``
        Returns:
          tuple: ``(file, disk, controller_device, disk_device)``, opaque
          objects of which any or all may be ``None``
        """
        raise NotImplementedError("search_from_controller not implemented")

    def find_open_controller(self, controller_type):
        """Find the first open slot on a controller of the given type.

        Args:
          controller_type (str): ``'ide'`` or ``'scsi'``
        Returns:
          tuple: ``(controller_device, address_string)`` or ``(None, None)``
        """
        raise NotImplementedError("find_open_controller not implemented")

    def get_id_from_file(self, file_obj):
        """Get the file ID from the given opaque file object.

        Args:
          file_obj (object): File object to query
        Returns:
          str: Identifier string associated with this object
        """
        raise NotImplementedError("get_id_from_file not implemented")

    def get_path_from_file(self, file_obj):
        """Get the file path from the given opaque file object.

        Args:
          file_obj (object): File object to query
        Returns:
          str: Relative path to the file associated with this object
        """
        raise NotImplementedError("get_path_from_file not implemented")

    def get_file_ref_from_disk(self, disk):
        """Get the file reference from the given opaque disk object.

        Args:
          disk (object): Disk object to query
        Returns:
          str: String that can be used to identify the file associated with
          this disk
        """
        raise NotImplementedError("get_file_ref_from_disk not implemented")

    def get_id_from_disk(self, disk):
        """Get the identifier string associated with the given Disk object.

        Args:
          disk (object): Disk object
        Returns:
          str: Identifier string associated with this object
        """
        raise NotImplementedError("get_id_from_disk not implemented")

    def get_common_subtype(self, device_type):
        """Get the sub-type common to all devices of the given type.

        Args:
          device_type (str): Device type such as ``'ide'`` or ``'memory'``.
        Returns:
          str: Subtype string common to all devices of this type, or ``None``,
          if multiple such devices exist and they do not all have the same
          sub-type.
        """
        raise NotImplementedError("get_common_subtype not implemented")

    def check_sanity_of_disk_device(self, disk, file_obj,
                                    disk_item, ctrl_item):
        """Check if the given disk is linked properly to the other objects.

        Args:
          disk (object): Disk object to validate
          file_obj (object): File object which this disk should be linked to
              (optional)
          disk_item (object): Disk device object which should link to
              this disk (optional)
          ctrl_item (object): Controller device object which should link to
              the :attr:`disk_item`
        Raises:
          ValueMismatchError: if the given items are not linked properly.
        """
        raise NotImplementedError(
            "check_sanity_of_disk_device not implemented")

    def add_file(self, file_path, file_id, file_obj=None, disk=None):
        """Add a new file object to the VM or overwrite the provided one.

        Args:
          file_path (str): Path to file to add
          file_id (str): Identifier string for the file in the VM
          file_obj (object): Existing file object to overwrite
          disk (object): Existing disk object referencing :attr:`file`.

        Returns:
          object: New or updated file object
        """
        raise NotImplementedError("add_file not implemented")

    def remove_file(self, file_obj, disk=None, disk_drive=None):
        """Remove the given file object from the VM.

        Args:
          file_obj (object): File object to remove
          disk (object): Disk object referencing :attr:`file`
          disk_drive (object): Disk drive mapping :attr:`file` to a device
        """
        raise NotImplementedError("remove_file not implemented")

    def add_disk(self, disk_repr, file_id, drive_type, disk=None):
        """Add a new disk object to the VM or overwrite the provided one.

        Args:
          disk_repr (DiskRepresentation): Disk file representation
          file_id (str): Identifier string for the file/disk mapping
          drive_type (str): 'harddisk' or 'cdrom'
          disk (object): Existing disk object to overwrite

        Returns:
          object: New or updated disk object
        """
        raise NotImplementedError("add_disk not implemented")

    def add_controller_device(self, device_type, subtype, address,
                              ctrl_item=None):
        """Create a new IDE or SCSI controller, or update existing one.

        Args:
          device_type (str): ``'ide'`` or ``'scsi'``
          subtype (str): Subtype such as ``'virtio'`` (optional)
          address (int): Controller address such as 0 or 1 (optional)
          ctrl_item (object): Existing controller device to update (optional)

        Returns:
          object: New or updated controller device object
        """
        raise NotImplementedError("add_controller_device not implemented")

    def add_disk_device(self, drive_type, address, name, description,
                        disk, file_obj, ctrl_item, disk_item=None):
        """Add a new disk device to the VM or update the provided one.

        Args:
          drive_type (str): ``'harddisk'`` or ``'cdrom'``
          address (str): Address on controller, such as "1:0" (optional)
          name (str): Device name string (optional)
          description (str): Description string (optional)
          disk (object): Disk object to map to this device
          file_obj (object): File object to map to this device
          ctrl_item (object): Controller object to serve as parent
          disk_item (object): Existing disk device to update instead of
              making a new device.

        Returns:
          object: New or updated disk device object.
        """
        raise NotImplementedError("add_disk_device not implemented")

    # API methods needed for edit-hardware
    def create_configuration_profile(self, pid, label, description):
        """Create/update a configuration profile with the given ID.

        Args:
          pid (str): Profile identifier
          label (str): Brief descriptive label for the profile
          description (str): Verbose description of the profile
        """
        raise NotImplementedError("create_configuration_profile "
                                  "not implemented!")

    def delete_configuration_profile(self, profile):
        """Delete the configuration profile with the given ID.

        Args:
          profile (str): Profile identifier
        """
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

        Args:
          cpus (int): Number of CPUs
          profile_list (list): Change only the given profiles
        """
        raise NotImplementedError("set_cpu_count not implemented!")

    def set_memory(self, megabytes, profile_list):
        """Set the amount of RAM, in megabytes.

        Args:
          megabytes (int): Memory value, in megabytes
          profile_list (list): Change only the given profiles
        """
        raise NotImplementedError("set_memory not implemented!")

    def set_nic_type(self, nic_type, profile_list):
        """Set the hardware type for NICs.

        .. deprecated:: 1.5
           Use :func:`set_nic_types` instead.

        Args:
          nic_type (str): NIC hardware type
          profile_list (list): Change only the given profiles.
        """
        warnings.warn("Use set_nic_types() instead", DeprecationWarning)
        self.set_nic_types([nic_type], profile_list)

    def set_nic_types(self, type_list, profile_list):
        """Set the hardware type(s) for NICs.

        Args:
          type_list (list): NIC hardware type(s)
          profile_list (list): Change only the given profiles.
        """
        raise NotImplementedError("set_nic_types not implemented!")

    def get_nic_count(self, profile_list):
        """Get the number of NICs under the given profile(s).

        Args:
          profile_list (list): Profile(s) of interest.
        Returns:
          dict: ``{ profile_name : nic_count }``
        """
        raise NotImplementedError("get_nic_count not implemented!")

    def set_nic_count(self, count, profile_list):
        """Set the given profile(s) to have the given number of NICs.

        Args:
          count (int): number of NICs
          profile_list (list): Change only the given profiles
        """
        raise NotImplementedError("set_nic_count not implemented!")

    def create_network(self, label, description):
        """Define a new network with the given label and description.

        Also serves to update the description of an existing network label.

        Args:
          label (str): Brief label for the network
          description (str): Verbose description of the network
        """
        raise NotImplementedError("create_network not implemented!")

    def set_nic_networks(self, network_list, profile_list):
        """Set the NIC to network mapping for NICs under the given profile(s).

        .. note::
          If the length of :attr:`network_list` is less than the number of
          NICs, will use the last entry in the list for all remaining NICs.

        Args:
          network_list (list): List of networks to map NICs to
          profile_list (list): Change only the given profiles
        """
        raise NotImplementedError("set_nic_networks not implemented!")

    def set_nic_mac_addresses(self, mac_list, profile_list):
        """Set the MAC addresses for NICs under the given profile(s).

        .. note::
          If the length of :attr:`mac_list` is less than the number of NICs,
          will use the last entry in the list for all remaining NICs.

        Args:
          mac_list (list): List of MAC addresses to assign to NICs
          profile_list (list): Change only the given profiles
        """
        raise NotImplementedError("set_nic_mac_addresses not implemented!")

    def set_nic_names(self, name_list, profile_list):
        """Set the device names for NICs under the given profile(s).

        Args:
          name_list (list): List of names to assign.
          profile_list (list): Change only the given profiles
        """
        raise NotImplementedError("set_nic_names not implemented!")

    def get_serial_count(self, profile_list):
        """Get the number of serial ports under the given profile(s).

        Args:
          profile_list (list): Change only the given profiles
        Returns:
          dict: ``{ profile_name : serial_count }``
        """
        raise NotImplementedError("get_serial_count not implemented!")

    def set_serial_count(self, count, profile_list):
        """Set the given profile(s) to have the given number of NICs.

        Args:
          count (int): Number of serial ports
          profile_list (list): Change only the given profiles
        """
        raise NotImplementedError("set_serial_count not implemented!")

    def set_serial_connectivity(self, conn_list, profile_list):
        """Set the serial port connectivity under the given profile(s).

        Args:
          conn_list (list): List of connectivity strings
          profile_list (list): Change only the given profiles
        """
        raise NotImplementedError("set_serial_connectivity not implemented!")

    def get_serial_connectivity(self, profile):
        """Get the serial port connectivity strings under the given profile.

        Args:
          profile (str): Profile of interest.
        Returns:
          list: List of connectivity strings
        """
        raise NotImplementedError("get_serial_connectivity not implemented!")

    def set_scsi_subtype(self, subtype, profile_list):
        """Set the device subtype for the SCSI controller(s).

        .. deprecated:: 1.5
           Use :func:`set_scsi_subtypes` instead.

        Args:
          subtype (str): SCSI subtype string
          profile_list (list): Change only the given profiles
        """
        warnings.warn("Use set_scsi_subtypes() instead", DeprecationWarning)
        self.set_scsi_subtypes([subtype], profile_list)

    def set_scsi_subtypes(self, type_list, profile_list):
        """Set the device subtype list for the SCSI controller(s).

        Args:
          type_list (list): SCSI subtype string list
          profile_list (list): Change only the given profiles
        """
        raise NotImplementedError("set_scsi_subtypes not implemented!")

    def set_ide_subtype(self, subtype, profile_list):
        """Set the device subtype for the IDE controller(s).

        .. deprecated:: 1.5
           Use :func:`set_ide_subtypes` instead.

        Args:
          subtype (str): IDE subtype string
          profile_list (list): Change only the given profiles
        """
        warnings.warn("Use set_ide_subtypes() instead", DeprecationWarning)
        self.set_ide_subtypes([subtype], profile_list)

    def set_ide_subtypes(self, type_list, profile_list):
        """Set the device subtype list for the IDE controller(s).

        Args:
          type_list (list): IDE subtype string list
          profile_list (list): Change only the given profiles
        """
        raise NotImplementedError("set_ide_subtypes not implemented!")

    # API methods needed for edit-product
    # API methods needed for edit-properties
    def get_property_value(self, key):
        """Get the value of the given property.

        Args:
          key (str): Property identifier
        Returns:
          str: Value of this property, or ``None``
        """
        raise NotImplementedError("get_property_value not implemented")

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
        """
        raise NotImplementedError("set_property_value not implemented")

    def config_file_to_properties(self, file_path, user_configurable=None):
        """Import each line of a text file into a configuration property.

        Args:
          file_path (str): File name to import.
          user_configurable (bool): Should the properties be configurable at
              deployment time by the user?
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

        Args:
          width (int): Line length to wrap to where possible.
          verbosity_option (str): 'brief', None (default), or 'verbose'

        Returns:
          str: Wrapped, appropriately verbose string.
        """
        raise NotImplementedError("info_string not implemented")

    def profile_info_string(self, width=79, verbosity_option=None):
        """Get a string summarizing available configuration profiles.

        Args:
          width (int): Line length to wrap to if possible
          verbosity_option (str): 'brief', None (default), or 'verbose'

        Returns:
          str: Appropriately formatted and verbose string.
        """
        raise NotImplementedError("profile_info_string not implemented")

    # API methods needed for inject-config
    def find_empty_drive(self, drive_type):
        """Find a disk device that exists but contains no data.

        Args:
          drive_type (str): Disk drive type, such as 'cdrom' or 'harddisk'
        Returns:
          object: Hardware device object, or None.
        """
        raise NotImplementedError("find_empty_drive not implemented")

    def find_device_location(self, device):
        """Find the controller type and address of a given device object.

        Args:
          device (object): Hardware device object.
        Returns:
          tuple: ``(type, address)``, such as ``("ide", "1:0")``.
        """
        raise NotImplementedError("find_device_location not implemented")


if __name__ == "__main__":   # pragma: no cover
    import doctest
    doctest.testmod()
