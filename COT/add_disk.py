#!/usr/bin/env python
#
# add_disk.py - Implements "cot add-disk" command
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

import sys
import logging
import os.path

from .data_validation import InvalidInputError, ValueUnsupportedError
from .data_validation import check_for_conflict, device_address, match_or_die
from .submodule import COTSubmodule

logger = logging.getLogger(__name__)


class COTAddDisk(COTSubmodule):
    """Add or replace a disk in a virtual machine"""

    def __init__(self, UI):
        super(COTAddDisk, self).__init__(
            UI,
            [
                "DISK_IMAGE",
                "PACKAGE",
                "output",
                "type",
                "subtype",
                "file_id",
                "controller",
                "address",
                "diskname",
                "description",
            ])

    def validate_arg(self, arg, value):
        """Check whether it's OK to set the given argument to the given value.
        Returns either (True, massaged_value) or (False, reason)"""
        valid, value_or_reason = super(COTAddDisk, self).validate_arg(arg,
                                                                      value)
        if not valid or value_or_reason is None:
            return valid, value_or_reason
        value = value_or_reason

        if arg == "DISK_IMAGE":
            if not os.path.exists(value):
                return False, ("Specified disk '{0}' does not exist!"
                               .format(value))
        elif arg == "address":
            return self.validate_controller_address(None, value)
        elif arg == "controller":
            return self.validate_controller_address(value, None)

        return valid, value_or_reason

    def validate_controller_address(self, controller, address):
        if controller is not None:
            input_value = controller
            address = self.get_value("address")
        elif address is not None:
            input_value = address
            controller = self.get_value("controller")

        if controller is not None and address is not None:
            ctrl_addr = address.split(":")[0]
            disk_addr = address.split(":")[1]
            if controller == "scsi" and (int(ctrl_addr) > 3 or
                                         int(disk_addr) > 15):
                return False, "SCSI disk address must be between 0:0 and 3:15"
            elif controller == "ide" and (int(ctrl_addr) > 1 or
                                          int(disk_addr) > 1):
                return False, "IDE disk address must be between 0:0 and 1:1"

        return True, input_value

    def ready_to_run(self):
        """Are we ready to go?
        Returns the tuple (ready, reason)"""
        if self.get_value("DISK_IMAGE") is None:
            return False, "DISK_IMAGE is a mandatory argument!"
        elif self.get_value("address") is not None:
            if self.get_value("controller") is None:
                return False, ("When specifying an address you must also "
                               "specify the controller type")
        return super(COTAddDisk, self).ready_to_run()

    def run(self):
        super(COTAddDisk, self).run()

        add_disk_worker(self.vm,
                        UI=self.UI,
                        **self.args)

    def create_subparser(self, parent):
        p = parent.add_parser(
            'add-disk', add_help=False,
            usage=("""
  {0} add-disk --help
  {0} <opts> add-disk DISK_IMAGE PACKAGE [-o OUTPUT]
                      [-f FILE_ID] [-t {{harddisk,cdrom}}]
                      [-c {{ide,scsi}}] [-s SUBTYPE] [-a ADDRESS]
                      [-d DESCRIPTION] [-n DISKNAME]"""
                   .format(os.path.basename(sys.argv[0]))),
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

        return 'add-disk', p


def add_disk_worker(vm,
                    UI,
                    DISK_IMAGE,
                    type=None,
                    subtype=None,
                    file_id=None,
                    controller=None,
                    address=None,
                    diskname=None,
                    description=None,
                    **kwargs):
        """Worker function for actually adding the disk"""

        if type is None:
            disk_extension = os.path.splitext(DISK_IMAGE)[1]
            ext_type_map = {
                '.iso':   'cdrom',
                '.vmdk':  'harddisk',
                '.raw':   'harddisk',
                '.qcow2': 'harddisk',
                '.img':   'harddisk',
                }
            try:
                type = ext_type_map[disk_extension]
            except KeyError:
                raise InvalidInputError(
                    "Unable to guess disk type for file '{0}' "
                    "from its extension '{1}'.\n"
                    "Known extensions are {2}\n"
                    "Please specify '--type harddisk' or '--type cdrom'."
                    .format(DISK_IMAGE, disk_extension,
                            ext_type_map.keys()))
            logger.warning("New disk type not specified, guessing it should "
                           "be '{0}' based on file extension".format(type))

        # Convert the disk to a new format if needed...
        DISK_IMAGE = vm.convert_disk_if_needed(DISK_IMAGE, type)

        disk_file = os.path.basename(DISK_IMAGE)

        # A disk is defined by up to four different sections in the OVF:
        #
        # File (references the actual disk image file)
        # Disk (references the File, only used for HD not CD-ROM)
        # Item (defines the SCSI/IDE controller)
        # Item (defines the disk drive, links to controller and File or Disk)
        #
        # For each of these four sections, we need to know whether to add
        # a new one or overwrite an existing one. Depending on the user
        # arguments, we can do this by as many as three different approaches:
        #
        # 1) Check whether the DISK_IMAGE file name matches an existing File
        #    in the OVF (and from there, find the associated Disk and Items)
        # 2) Check whether the --file-id matches an existing File and/or Disk
        #    in the OVF (and from there, find the associated Items)
        # 3) Check whether --controller and/or --address match existing Items
        #    in the OVF (and from there, find the associated Disk and/or File)
        #
        # Where it gets extra fun is if the user has specified more than one
        # of the above arguments - in which case we need to make sure that
        # all relevant approaches agree on what sections we're talking about...

        # 1) Check whether the DISK_IMAGE file name matches an existing File
        #    in the OVF (and from there, find the associated Disk and Items)
        (f1, d1, ci1, di1) = vm.search_from_filename(disk_file)

        # 2) Check whether the --file-id matches an existing File and/or Disk
        #    in the OVF (and from there, find the associated Items)
        (f2, d2, ci2, di2) = vm.search_from_file_id(file_id)

        # 3) Check whether the --controller and --address match existing Items
        #    in the OVF (and from there, find the associated Disk and/or File)
        (f3, d3, ci3, di3) = vm.search_from_controller(controller,
                                                       address)

        file = check_for_conflict("File to overwrite", [f1, f2, f3])
        disk = check_for_conflict("Disk to overwrite", [d1, d2, d3])
        ctrl_item = check_for_conflict("controller Item to use",
                                       [ci1, ci2, ci3])
        disk_item = check_for_conflict("disk Item to overwrite",
                                       [di1, di2, di3])

        # Ok, we now have confirmed that we have at most one of each of these
        # four objects. Now it's time for some sanity checking...

        if file is not None:
            if file_id is not None:
                match_or_die("File id", vm.get_id_from_file(file),
                             "--file-id", file_id)
            # Should never fail this test if the above logic was sound...
            if disk is not None:
                match_or_die("File id", vm.get_id_from_file(file),
                             "Disk fileRef", vm.get_file_ref_from_disk(disk))

        if disk is not None:
            if file_id is not None:
                match_or_die("Disk fileRef", vm.get_file_ref_from_disk(disk),
                             "--file-id", file_id)
            if file is None:
                # This will happen if we're replacing a placeholder entry
                # (disk exists but has no associated file)
                logger.verbose("Found Disk but not File - maybe placeholder?")

        if disk_item is not None:
            if type is not None:
                match_or_die("disk Item ResourceType",
                             vm.get_type_from_device(disk_item),
                             "--type", type)
            else:
                type = vm.get_type_from_device(disk_item)
                logger.info("Guessing disk type '{0}' from existing disk Item"
                            .format(type))
            vm.check_sanity_of_disk_device(disk, file, disk_item, ctrl_item)

        if ctrl_item is not None:
            if controller is not None:
                match_or_die("controller type",
                             vm.get_type_from_device(ctrl_item),
                             "--controller", controller)
            else:
                controller = vm.get_type_from_device(ctrl_item)
                if controller != 'ide' and controller != 'scsi':
                    raise ValueUnsupportedError("controller ResourceType",
                                                controller,
                                                "'ide' or 'scsi'")
                logger.info("Guessing controller type '{0}' from existing Item"
                            .format(controller))
        else:
            # If the user didn't tell us which controller type they wanted,
            # and we didn't find a controller item based on existing file/disk,
            # then we need to guess which type of controller we need,
            # based on the platform and the disk type.
            if controller is None:
                platform = vm.get_platform()
                controller = platform.controller_type_for_device(type)
                logger.warning("Guessing controller type should be {0} "
                               "based on disk type {1} and platform {2}"
                               .format(controller, type,
                                       platform.__name__))

            if address is None:
                # We didn't find a specific controller from the user info,
                # but also the user didn't request a specific controller.
                # So try and just look for any controller of the right type
                (ctrl_item, address) = vm.find_open_controller(
                    controller)

        logger.debug("Validation of existing data complete")

        # Whew! Everything looks sane!

        if file is not None:
            UI.confirm_or_die("Replace existing file {0} with {1}?"
                              .format(vm.get_path_from_file(file),
                                      DISK_IMAGE))
            logger.warning("Overwriting existing File in OVF")

        if file is None and (disk is not None or disk_item is not None):
            UI.confirm_or_die(
                "Add disk file to existing (but empty) {0} drive?"
                .format(type))

        if disk is not None:
            logger.warning("Overwriting existing Disk in OVF")

        if disk_item is not None:
            # We'll overwrite the existing disk Item instead of deleting
            # and recreating it, in order to preserve things like Description
            logger.warning("Overwriting existing disk Item in OVF")

        if ctrl_item is not None:
            if subtype is not None:
                curr_subtype = vm.get_subtype_from_device(ctrl_item)
                if curr_subtype is not None and curr_subtype != subtype:
                    UI.confirm_or_die("Change {0} controller subtype from "
                                      "'{1}' to '{2}'?".format(controller,
                                                               curr_subtype,
                                                               subtype))
        else:
            # In most cases we are NOT adding a new controller, so be safe...
            UI.confirm_or_die("Add new {0} controller to OVF descriptor?"
                              .format(controller.upper()))
            if subtype is None:
                # Look for any existing controller of this type;
                # if found, re-use its subtype for consistency
                logger.verbose("Looking for subtype of existing controllers")
                subtype = vm.get_common_subtype(controller)

        # OK - let's add things!
        if file_id is None and file is not None:
            file_id = vm.get_id_from_file(file)
        if file_id is None and disk is not None:
            file_id = vm.get_file_ref_from_disk(disk)
        if file_id is None:
            file_id = disk_file

        # First, the File
        file = vm.add_file(DISK_IMAGE, file_id, file, disk)

        # Next, the Disk
        disk = vm.add_disk(DISK_IMAGE, file_id, type, disk)

        # Next, the controller (if needed)
        if address is not None:
            ctrl_addr = address.split(":")[0]
            disk_addr = address.split(":")[1]
        else:
            # let VM choose controller address if necessary
            ctrl_addr = None
            disk_addr = 0

        ctrl_item = vm.add_controller_device(controller, subtype,
                                             ctrl_addr, ctrl_item)

        # Finally, the disk Item
        vm.add_disk_device(type, disk_addr, diskname,
                           description, disk, file, ctrl_item, disk_item)
