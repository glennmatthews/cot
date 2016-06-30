#!/usr/bin/env python
#
# add_disk.py - Implements "cot add-disk" command
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

"""Module for adding disks to VMs.

**Functions**

.. autosummary::
  :nosignatures:

  add_disk_worker
  confirm_elements
  guess_controller_type
  guess_disk_type_from_extension
  search_for_elements
  validate_elements
  validate_controller_address

**Classes**

.. autosummary::
  :nosignatures:

  COTAddDisk
"""

import logging
import os.path

from .data_validation import InvalidInputError, ValueUnsupportedError
from .data_validation import check_for_conflict, device_address, match_or_die
from .submodule import COTSubmodule

logger = logging.getLogger(__name__)


def validate_controller_address(controller, address):
    """Check validity of the given address string for the given controller.

    Helper method for the :attr:`controller`/:attr:`address` setters.

    :param str controller: ``'ide'`` or ``'scsi'``
    :param str address: A string like '0:0' or '2:10'
    :raises: :exc:`.InvalidInputError` if the address/controller combo
                                       is invalid.
    """
    logger.info("validate_controller_address: %s, %s", controller, address)
    if controller is not None and address is not None:
        logger.info("Validating controller/address combo")
        ctrl_addr = address.split(":")[0]
        disk_addr = address.split(":")[1]
        if controller == "scsi" and (int(ctrl_addr) > 3 or
                                     int(disk_addr) > 15):
            raise InvalidInputError(
                "SCSI disk address must be between 0:0 and 3:15")
        elif controller == "ide" and (int(ctrl_addr) > 1 or
                                      int(disk_addr) > 1):
            raise InvalidInputError(
                "IDE disk address must be between 0:0 and 1:1")


class COTAddDisk(COTSubmodule):
    """Add or replace a disk in a virtual machine.

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`,
    :attr:`~COTSubmodule.package`,
    :attr:`~COTSubmodule.output`

    Attributes:
    :attr:`disk_image`,
    :attr:`type`,
    :attr:`file_id`,
    :attr:`controller`,
    :attr:`subtype`,
    :attr:`address`,
    :attr:`diskname`,
    :attr:`description`
    """

    def __init__(self, ui):
        """Instantiate this submodule with the given UI."""
        super(COTAddDisk, self).__init__(ui)
        self._disk_image = None
        self.disk_type = None
        """Disk type ('harddisk' or 'cdrom')."""
        self.subtype = None
        """Controller subtype, such as "virtio"."""
        self.file_id = None
        """File identifier to map disk to file."""
        self._controller = None
        self._address = None
        self.diskname = None
        """Name string for the disk."""
        self.description = None
        """Description of the disk."""

    @property
    def disk_image(self):
        """Path to disk image file to add to the VM.

        :raises: :exc:`.InvalidInputError` if the file does not exist.
        """
        return self._disk_image

    @disk_image.setter
    def disk_image(self, value):
        if not os.path.exists(value):
            raise InvalidInputError("Specified disk '{0}' does not exist!"
                                    .format(value))
        self._disk_image = value

    @property
    def address(self):
        """Disk device address on controller (``1:0``, etc.).

        :raises: :exc:`.InvalidInputError`,
          see :meth:`validate_controller_address`
        """
        return self._address

    @address.setter
    def address(self, value):
        logger.info("Setting address to '%s'", value)
        validate_controller_address(self.controller, value)
        self._address = value

    @property
    def controller(self):
        """Disk controller type (``ide``, ``scsi``).

        :raises: :exc:`.InvalidInputError`,
          see :meth:`validate_controller_address`
        """
        return self._controller

    @controller.setter
    def controller(self, value):
        logger.info("Setting controller to '%s'", value)
        validate_controller_address(value, self.address)
        self._controller = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.disk_image is None:
            return False, "DISK_IMAGE is a mandatory argument!"
        elif self.address is not None and self.controller is None:
            return False, ("When specifying an address you must also "
                           "specify the controller type")
        return super(COTAddDisk, self).ready_to_run()

    def run(self):
        """Do the actual work of this submodule.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTAddDisk, self).run()

        add_disk_worker(self.vm,
                        ui=self.UI,
                        disk_image=self.disk_image,
                        disk_type=self.disk_type,
                        subtype=self.subtype,
                        file_id=self.file_id,
                        controller=self.controller,
                        address=self.address,
                        diskname=self.diskname,
                        description=self.description)

    def create_subparser(self):
        """Create 'add-disk' CLI subparser."""
        p = self.UI.add_subparser(
            'add-disk',
            aliases=['add-drive'],
            add_help=False,
            usage=self.UI.fill_usage("add-disk", [
                "DISK_IMAGE PACKAGE [-o OUTPUT] [-f FILE_ID] \
[-t {harddisk,cdrom}] [-c {ide,scsi}] [-s SUBTYPE] [-a ADDRESS] \
[-d DESCRIPTION] [-n DISKNAME]"
            ]),
            help="""Add a disk image to an OVF package and map it as a disk
in the guest environment""",
            description="""
Add or replace a disk image in the specified OVF or OVA.
If the specified disk image, controller/address, file-id, and/or instance
match an existing entry in the OVF, will replace the existing disk with
the provided file (prompting for confirmation if --force was not set);
otherwise, will create a new disk entry.""")

        group = p.add_argument_group("general options")

        group.add_argument('-h', '--help', action='help',
                           help="""Show this help message and exit""")
        group.add_argument('-o', '--output',
                           help="""Name/path of new OVF/OVA package to """
                           """create instead of updating the existing OVF""")

        group = p.add_argument_group("disk-related options")

        group.add_argument('-f', '--file-id',
                           help="""Disk image file ID string within the OVF """
                           """package (default: use disk image filename)""")
        group.add_argument('-t', '--type',
                           dest='disk_type',
                           choices=['harddisk', 'cdrom'],
                           help="""Disk type (default: files ending in """
                           """.vmdk/.raw/.qcow2/.img will use harddisk """
                           """and files ending in .iso will use cdrom)""")

        group = p.add_argument_group("controller-related options")

        group.add_argument('-c', '--controller',
                           choices=['ide', 'scsi'],
                           help="""Disk controller type (default: """
                           """determined by disk type and platform)""")
        group.add_argument('-a', '--address', type=device_address,
                           help="""Address of the disk, such as "1:0". """
                           """Requires that --controller be explicitly set. """
                           """(default: use first unused address on the """
                           """controller)""")
        group.add_argument('-s', '--subtype',
                           help="""Disk controller subtype such as "virtio" """
                           """or "lsilogic".""")

        group = p.add_argument_group("descriptive options")

        group.add_argument('-d', '--description',
                           help="""Description of this disk (optional)""")
        group.add_argument('-n', '--name', dest='diskname',
                           help="""Name of this disk (default: """
                           """"Hard disk #" or "CD-ROM #" as appropriate)""")

        p.add_argument('DISK_IMAGE',
                       help="""Disk image file to add to the package""")
        p.add_argument('PACKAGE',
                       help="""OVF descriptor or OVA file to edit""")
        p.set_defaults(instance=self)


def guess_disk_type_from_extension(disk_file):
    """Guess the disk type (harddisk/cdrom) from the disk file name."""
    disk_extension = os.path.splitext(disk_file)[1]
    ext_type_map = {
        '.iso':   'cdrom',
        '.vmdk':  'harddisk',
        '.raw':   'harddisk',
        '.qcow2': 'harddisk',
        '.img':   'harddisk',
    }
    try:
        disk_type = ext_type_map[disk_extension]
    except KeyError:
        raise InvalidInputError(
            "Unable to guess disk type for file '{0}' from its extension "
            "'{1}'.\nKnown extensions are {2}\n"
            "Please specify '--type harddisk' or '--type cdrom'."
            .format(disk_file, disk_extension, ext_type_map.keys()))
    return disk_type


def search_for_elements(vm, disk_file, file_id, controller, address):
    """Search for a unique set of objects based on the given criteria.

    A disk is defined by up to four different sections in the OVF:

    File (references the actual disk image file)
    Disk (references the File, only used for HD not CD-ROM)
    Item (defines the SCSI/IDE controller)
    Item (defines the disk drive, links to controller and File or Disk)

    For each of these four sections, we need to know whether to add
    a new one or overwrite an existing one. Depending on the user
    arguments, we can do this by as many as three different approaches:

    1. Check whether the DISK_IMAGE file name matches an existing File
       in the OVF (and from there, find the associated Disk and Items)
    2. Check whether the file-id matches an existing File and/or Disk
       in the OVF (and from there, find the associated Items)
    3. Check whether controller type and/or device address match existing Items
       in the OVF (and from there, find the associated Disk and/or File)

    Where it gets extra fun is if the user has specified more than one
    of the above arguments - in which case we need to make sure that
    all relevant approaches agree on what sections we're talking about...

    :raises ValueMismatchError: if the criteria select a non-unique set.
    :return: (file_object, disk_object, controller_item, disk_item)
    """
    # 1) Check whether the DISK_IMAGE file name matches an existing File
    #    in the OVF (and from there, find the associated Disk and Items)
    (f1, d1, ci1, di1) = vm.search_from_filename(disk_file)

    # 2) Check whether the --file-id matches an existing File and/or Disk
    #    in the OVF (and from there, find the associated Items)
    # In the case where no file_id is specified, we may default to the
    # filename, so check that instead
    if file_id is not None:
        (f2, d2, ci2, di2) = vm.search_from_file_id(file_id)
    else:
        (f2, d2, ci2, di2) = vm.search_from_file_id(disk_file)

    # 3) Check whether the --controller and --address match existing Items
    #    in the OVF (and from there, find the associated Disk and/or File)
    (f3, d3, ci3, di3) = vm.search_from_controller(controller,
                                                   address)

    file_obj = check_for_conflict("File to overwrite", [f1, f2, f3])
    disk_obj = check_for_conflict("Disk to overwrite", [d1, d2, d3])
    ctrl_item = check_for_conflict("controller Item to use",
                                   [ci1, ci2, ci3])
    disk_item = check_for_conflict("disk Item to overwrite",
                                   [di1, di2, di3])

    return file_obj, disk_obj, ctrl_item, disk_item


def guess_controller_type(vm, ctrl_item, disk_type):
    """If a controller type wasn't specified, try to guess from context."""
    if ctrl_item is None:
        # If the user didn't tell us which controller type they wanted,
        # and we didn't find a controller item based on existing file/disk,
        # then we need to guess which type of controller we need,
        # based on the platform and the disk type.
        ctrl_type = vm.platform.controller_type_for_device(disk_type)
        logger.warning("Guessing controller type should be %s "
                       "based on disk type %s and platform %s",
                       ctrl_type, disk_type, vm.platform.__name__)
    else:
        ctrl_type = vm.get_type_from_device(ctrl_item)
        if ctrl_type != 'ide' and ctrl_type != 'scsi':
            raise ValueUnsupportedError("controller ResourceType",
                                        ctrl_type,
                                        "'ide' or 'scsi'")
        logger.info("Guessing controller type '%s' from existing Item",
                    ctrl_type)
    return ctrl_type


def validate_elements(vm, file_obj, disk_obj, disk_item, ctrl_item,
                      file_id, ctrl_type):
    """Validate any existing file, disk, controller item, and disk item.

    :raises ValueMismatchError: if the search criteria select a non-unique set.
    """
    # Ok, we now have confirmed that we have at most one of each of these
    # four objects. Now it's time for some sanity checking...

    if file_obj is not None:
        if file_id is not None:
            match_or_die("File id", vm.get_id_from_file(file_obj),
                         "--file-id", file_id)
        # Should never fail this test if the above logic was sound...
        if disk_obj is not None:
            match_or_die("File id", vm.get_id_from_file(file_obj),
                         "Disk fileRef", vm.get_file_ref_from_disk(disk_obj))

    if disk_obj is not None:
        if file_id is not None:
            match_or_die("Disk fileRef", vm.get_file_ref_from_disk(disk_obj),
                         "--file-id", file_id)
        if file_obj is None:
            # This will happen if we're replacing a placeholder entry
            # (disk exists but has no associated file)
            logger.verbose("Found Disk but not File - maybe placeholder?")

    if disk_item is not None:
        vm.check_sanity_of_disk_device(disk_obj, file_obj,
                                       disk_item, ctrl_item)

    if ctrl_item is not None:
        match_or_die("controller type",
                     vm.get_type_from_device(ctrl_item),
                     "--controller", ctrl_type)

    # Whew! Everything looks sane!
    logger.debug("Validation of existing data complete")


def confirm_elements(vm, ui, file_obj, disk_image, disk_obj, disk_item,
                     disk_type, controller, ctrl_item, subtype):
    """Get user confirmation of any risky or unusual operations."""
    # TODO: more refactoring!
    if file_obj is not None:
        ui.confirm_or_die("Replace existing file {0} with {1}?"
                          .format(vm.get_path_from_file(file_obj),
                                  disk_image))
        logger.warning("Overwriting existing File in OVF")

    if file_obj is None and (disk_obj is not None or disk_item is not None):
        ui.confirm_or_die(
            "Add disk file to existing (but empty) {0} drive?"
            .format(disk_type))

    if disk_obj is not None:
        logger.warning("Overwriting existing Disk in OVF")

    if disk_item is not None:
        ui.confirm_or_die("Existing disk Item is a {0}. Change it to a {1}?"
                          .format(vm.get_type_from_device(disk_item),
                                  disk_type))
        # We'll overwrite the existing disk Item instead of deleting
        # and recreating it, in order to preserve things like Description
        logger.warning("Overwriting existing disk Item in OVF")

    if ctrl_item is not None:
        if subtype is not None:
            curr_subtype = vm.get_subtype_from_device(ctrl_item)
            if curr_subtype is not None and curr_subtype != subtype:
                ui.confirm_or_die("Change {0} controller subtype from "
                                  "'{1}' to '{2}'?".format(controller,
                                                           curr_subtype,
                                                           subtype))
    else:
        # In most cases we are NOT adding a new controller, so be safe...
        ui.confirm_or_die("Add new {0} controller to OVF descriptor?"
                          .format(controller.upper()))


def add_disk_worker(vm,
                    ui,
                    disk_image,
                    disk_type=None,
                    file_id=None,
                    controller=None,
                    subtype=None,
                    address=None,
                    diskname=None,
                    description=None):
    """Worker function for actually adding the disk.

    All parameters except ``vm``, ``ui``, and ``disk_image`` are optional
    and will be automatically determined by COT if unspecified.

    :param vm: The virtual machine being edited.
    :type vm: :class:`~COT.ovf.OVF` or other
        :class:`~COT.vm_description.VMDescription` subclass

    :param ui: User interface in effect.
    :type ui: instance of :class:`~COT.ui_shared.UI` or subclass.
    :param str disk_image: path to disk image to add to the VM.
    :param str disk_type: Disk type: ``'cdrom'`` or ``'harddisk'``.
        If not specified, will be derived automatically from the
        disk_image file name extension.

    :param str file_id: Identifier of the disk file in the VM. If not
        specified, the VM will automatically derive an appropriate value.

    :param str controller: Disk controller type: ``'ide'`` or ``'scsi'``.
        If not specified, will be derived from the `type` and the
        `platform` of the given `vm`.

    :param str subtype: Controller subtype ('virtio', 'lsilogic', etc.)
    :param str address: Disk device address on its controller
        (such as ``'1:0'``). If this matches an existing disk device,
        that device will be overwritten. If not specified, the first
        available address not already occupied by an existing device
        will be selected.

    :param str diskname: Name for disk device
    :param str description: Description of disk device
    """
    if disk_type is None:
        disk_type = guess_disk_type_from_extension(disk_image)
        logger.warning("New disk type not specified, guessing it should "
                       "be '%s' based on file extension", disk_type)

    # Convert the disk to a new format if needed...
    disk_image = vm.convert_disk_if_needed(disk_image, disk_type)

    disk_file = os.path.basename(disk_image)

    (file_obj, disk, ctrl_item, disk_item) = \
        search_for_elements(vm, disk_file, file_id, controller, address)

    if controller is None:
        controller = guess_controller_type(vm, ctrl_item, disk_type)

    if ctrl_item is None and address is None:
        # We didn't find a specific controller from the user info,
        # but also the user didn't request a specific controller.
        # So try and just look for any controller of the right type
        (ctrl_item, address) = vm.find_open_controller(controller)

    validate_elements(vm, file_obj, disk, disk_item, ctrl_item,
                      file_id, controller)

    confirm_elements(vm, ui, file_obj, disk_image, disk, disk_item, disk_type,
                     controller, ctrl_item, subtype)

    # OK - let's add things!
    if file_id is None and file_obj is not None:
        file_id = vm.get_id_from_file(file_obj)
    if file_id is None and disk is not None:
        file_id = vm.get_file_ref_from_disk(disk)
    if file_id is None:
        file_id = disk_file

    # First, the File
    file_obj = vm.add_file(disk_image, file_id, file_obj, disk)

    # Next, the Disk
    disk = vm.add_disk(disk_image, file_id, disk_type, disk)

    # Next, the controller (if needed)
    if address is not None:
        ctrl_addr = address.split(":")[0]
        disk_addr = address.split(":")[1]
    else:
        # let VM choose controller address if necessary
        ctrl_addr = None
        disk_addr = None

    if ctrl_item is None and subtype is None:
        # Look for any existing controller of this type;
        # if found, re-use its subtype for consistency
        logger.verbose("Looking for subtype of existing controllers")
        subtype = vm.get_common_subtype(controller)

    ctrl_item = vm.add_controller_device(controller, subtype,
                                         ctrl_addr, ctrl_item)

    # Finally, the disk Item
    vm.add_disk_device(disk_type, disk_addr, diskname,
                       description, disk, file_obj, ctrl_item, disk_item)
