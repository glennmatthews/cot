#!/usr/bin/env python
#
# add_disk.py - Implements "cot add-disk" command
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

import sys
import logging
import os.path

from .cli import subparsers, subparser_lookup, confirm_or_die, device_address
from .vm_context_manager import VMContextManager
from .data_validation import *

logger = logging.getLogger('cot')

def add_disk(args):
    """Add or replace a disk in a virtual machine"""

    if args.address is not None:
        if args.controller is None:
            p_add_disk.error("When using --address you must also use "
                             "--controller")
        ctrl_addr = args.address.split(":")[0]
        disk_addr = args.address.split(":")[1]
        if args.controller == "scsi" and (int(ctrl_addr) > 3 or
                                          int(disk_addr) > 15):
            p_add_disk.error("SCSI disk address must be between 0:0 and 3:15")
        elif args.controller == "ide" and (int(ctrl_addr) > 1 or
                                           int(disk_addr) > 1):
            p_add_disk.error("IDE disk address must be between 0:0 and 1:1")

    if not os.path.exists(args.DISK_IMAGE):
        p_add_disk.error("Specified disk {0} does not exist!"
                         .format(args.DISK_IMAGE))

    with VMContextManager(args.PACKAGE, args.output) as vm:
        add_disk_worker(vm, args)


def add_disk_worker(vm, args):
        """Worker function for actually adding the disk"""

        if args.type is None:
            disk_extension = os.path.splitext(args.DISK_IMAGE)[1]
            ext_type_map = {
                '.iso':   'cdrom',
                '.vmdk':  'harddisk',
                '.raw':   'harddisk',
                '.qcow2': 'harddisk',
                '.img':   'harddisk',
                }
            try:
                args.type = ext_type_map[disk_extension]
            except KeyError:
                p_add_disk.error("Unable to guess disk type for file '{0}' "
                                 "from its extension '{1}'.\n"
                                 "Known extensions are {2}\n"
                                 "Please specify '--type harddisk' or "
                                 "'--type cdrom'."
                                 .format(args.DISK_IMAGE, disk_extension,
                                         ext_type_map.keys()))
            logger.warning("New disk type not specified, guessing it should be "
                           "'{0}' based on file extension".format(args.type))

        # Convert the disk to a new format if needed...
        args.DISK_IMAGE = vm.convert_disk_if_needed(args.DISK_IMAGE, args.type)

        disk_file = os.path.basename(args.DISK_IMAGE)

        # A disk is defined by up to four different sections in the OVF:
        #
        # File (references the actual disk image file)
        # Disk (references the File, only used for HD not CD-ROM)
        # Item (defines the SCSI/IDE controller)
        # Item (defines the disk drive, links to controller and File or Disk)
        #
        # For each of these four sections, we need to know whether to add
        # a new one or overwrite an existing one. Depending on the user-provided
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
        (f2, d2, ci2, di2) = vm.search_from_file_id(args.file_id)

        # 3) Check whether the --controller and --address match existing Items
        #    in the OVF (and from there, find the associated Disk and/or File)
        (f3, d3, ci3, di3) = vm.search_from_controller(args.controller,
                                                       args.address)

        file = check_for_conflict("File to overwrite", [f1, f2, f3])
        disk = check_for_conflict("Disk to overwrite", [d1, d2, d3])
        ctrl_item = check_for_conflict("controller Item to use",
                                       [ci1, ci2, ci3])
        disk_item = check_for_conflict("disk Item to overwrite",
                                       [di1, di2, di3])

        # Ok, we now have confirmed that we have at most one of each of these
        # four objects. Now it's time for some sanity checking...

        if file is not None:
            if args.file_id is not None:
                match_or_die("File id", vm.get_id_from_file(file),
                             "--file-id", args.file_id)
            # Should never fail this test if the above logic was sound...
            if disk is not None:
                match_or_die("File id", vm.get_id_from_file(file),
                             "Disk fileRef", vm.get_file_ref_from_disk(disk))

        if disk is not None:
            if args.file_id is not None:
                match_or_die("Disk fileRef", vm.get_file_ref_from_disk(disk),
                             "--file-id", args.file_id)
            if file is None:
                # This will happen if we're replacing a placeholder entry
                # (disk exists but has no associated file)
                logger.info("Found Disk but not File - placeholder?")

        if disk_item is not None:
            if args.type is not None:
                match_or_die("disk Item ResourceType",
                             vm.get_type_from_device(disk_item),
                             "--type", args.type)
            else:
                args.type = vm.get_type_from_device(disk_item)
                logger.info("Guessing disk type '{0}' from existing disk Item"
                            .format(args.type))
            vm.check_sanity_of_disk_device(disk, file, disk_item, ctrl_item)

        if ctrl_item is not None:
            if args.controller is not None:
                match_or_die("controller type",
                             vm.get_type_from_device(ctrl_item),
                             "--controller", args.controller)
            else:
                args.controller = vm.get_type_from_device(ctrl_item)
                if args.controller != 'ide' and args.controller != 'scsi':
                    raise ValueUnsupportedError("controller ResourceType",
                                                args.controller,
                                                "'ide' or 'scsi'")
                logger.info("Guessing controller type '{0}' from existing Item"
                            .format(args.controller))
        else:
            # If the user didn't tell us which controller type they wanted,
            # and we didn't find a controller item based on existing file/disk,
            # then we need to guess which type of controller we need,
            # based on the platform and the disk type.
            if args.controller is None:
                platform = vm.get_platform()
                args.controller = platform.controller_type_for_device(args.type)
                logger.warning("Guessing controller type should be {0} "
                               "based on disk type {1} and platform {2}"
                               .format(args.controller, args.type,
                                       platform.__name__))

            if args.address is None:
                # We didn't find a specific controller from the user info,
                # but also the user didn't request a specific controller.
                # So try and just look for any controller of the right type
                (ctrl_item, args.address) = vm.find_open_controller(
                    args.controller)

        logger.debug("Validation of existing data complete")

        # Whew! Everything looks sane!

        if file is not None:
            confirm_or_die("Replace existing file {0} with {1}?"
                           .format(vm.get_path_from_file(file),
                                   args.DISK_IMAGE),
                           args.force)
            logger.warning("Overwriting existing File in OVF")

        if file is None and (disk is not None or disk_item is not None):
            confirm_or_die("Add disk file to existing (but empty) {0} drive?"
                           .format(args.type), args.force)

        if disk is not None:
            logger.warning("Overwriting existing Disk in OVF")

        if disk_item is not None:
            # We'll overwrite the existing disk Item instead of deleting
            # and recreating it, in order to preserve things like Description
            logger.warning("Overwriting existing disk Item in OVF")

        if ctrl_item is not None:
            if args.subtype is not None:
                curr_subtype = vm.get_subtype_from_device(ctrl_item)
                if curr_subtype is not None and curr_subtype != args.subtype:
                    confirm_or_die("Change {0} controller subtype from '{1}' "
                                   "to '{2}'?".format(args.controller,
                                                      curr_subtype,
                                                      args.subtype),
                                   args.force)
        else:
            # In most cases we are NOT adding a new controller, so be safe...
            confirm_or_die("Add new {0} controller to OVF descriptor?"
                           .format(args.controller.upper()),
                           args.force)
            if args.subtype is None:
                # Look for any existing controller of this type;
                # if found, re-use its subtype for consistency
                logger.info("Looking for subtype of existing controllers")
                args.subtype = vm.get_common_subtype(args.controller)

        # OK - let's add things!
        if args.file_id is None and file is not None:
            args.file_id = vm.get_id_from_file(file)
        if args.file_id is None and disk is not None:
            args.file_id = vm.get_file_ref_from_disk(disk)
        if args.file_id is None:
            args.file_id = disk_file

        # First, the File
        file = vm.add_file(args.DISK_IMAGE, args.file_id, file, disk)

        # Next, the Disk
        disk = vm.add_disk(args.DISK_IMAGE, args.file_id, args.type, disk)

        # Next, the controller (if needed)
        if args.address is not None:
            ctrl_addr = args.address.split(":")[0]
            disk_addr = args.address.split(":")[1]
        else:
            ctrl_addr = None # let VM choose it if necessary
            disk_addr = 0

        ctrl_item = vm.add_controller_device(args.controller, args.subtype,
                                             ctrl_addr, ctrl_item)

        # Finally, the disk Item
        vm.add_disk_device(args.type, disk_addr, args.diskname,
                           args.description, disk, file, ctrl_item, disk_item)


# Add ourselves to the parser options
p_add_disk = subparsers.add_parser(
    'add-disk', add_help=False,
    usage=("""
  {0} add-disk --help
  {0} [-f] [-v] add-disk DISK_IMAGE PACKAGE [-o OUTPUT]
                         [-f FILE_ID] [-t {{harddisk,cdrom}}]
                         [-c {{ide,scsi}}] [-s SUBTYPE] [-a ADDRESS]
                         [-d DESCRIPTION] [-n DISKNAME]"""
           .format(os.path.basename(sys.argv[0]))),
    help="""Add a disk image to an OVF package and map it as a disk in the
guest environment""",
    description="""
Add or replace a disk image in the specified OVF or OVA.
If the specified disk image, controller/address, file-id, and/or instance
match an existing entry in the OVF, will replace the existing disk with
the provided file (prompting for confirmation if --force was not set);
otherwise, will create a new disk entry.""")
subparser_lookup['add-disk'] = p_add_disk

p_ad_gen = p_add_disk.add_argument_group("general options")

p_ad_gen.add_argument('-h', '--help', action='help',
                      help="""Show this help message and exit""")
p_ad_gen.add_argument('-o', '--output',
                      help="""Name/path of new OVF/OVA package to create
                              instead of updating the existing OVF""")

p_ad_disk = p_add_disk.add_argument_group("disk-related options")

p_ad_disk.add_argument('-f', '--file-id',
                       help="""Disk image file ID string within the OVF package
                               (default: same as disk image filename)""")
p_ad_disk.add_argument('-t', '--type',
                       choices=['harddisk', 'cdrom'],
                       help="""Disk type (default: files ending in
                               .vmdk/.raw/.qcow2/.img will use harddisk
                               and files ending in .iso will use cdrom)""")

p_ad_cont = p_add_disk.add_argument_group("controller-related options")

p_ad_cont.add_argument('-c', '--controller',
                       choices=['ide', 'scsi'],
                       help="""Disk controller type (default: determined by
                               disk type and platform)""")
p_ad_cont.add_argument('-a', '--address', type=device_address,
                       help="""Address of the disk, such as "1:0". Requires
                               that --controller be explicitly set. (default:
                               use first unused address on the controller)""")
p_ad_cont.add_argument('-s', '--subtype',
                       help="""Disk controller subtype such as "virtio" or
                               "lsilogic".""")

p_ad_desc = p_add_disk.add_argument_group("descriptive options")

p_ad_desc.add_argument('-d', '--description',
                       help="""Description of this disk (optional)""")
p_ad_desc.add_argument('-n', '--name', dest='diskname',
                       help="""Name of this disk (default: "Hard disk #" or
                               "CD-ROM #" as appropriate)""")

p_add_disk.add_argument('DISK_IMAGE',
                        help="""Disk image file to add to the package""")
p_add_disk.add_argument('PACKAGE',
                        help="""OVF descriptor or OVA file to edit""")
p_add_disk.set_defaults(func=add_disk)
