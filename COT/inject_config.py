#!/usr/bin/env python
#
# inject_config.py - Implements "cot inject-config" command
#
# February 2014, Glenn F. Matthews
# Copyright (c) 2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

import argparse
import logging
import os.path
import shutil
import sys

from .add_disk import add_disk_worker
from .cli import subparsers, subparser_lookup
from .data_validation import ValueUnsupportedError
from .helper_tools import create_disk_image
from .vm_context_manager import VMContextManager

logger = logging.getLogger('cot')

def inject_config(args):
    """Wrap the given configuration file(s) into an appropriate disk image file
    and embed it into the given VM package.
    """

    # Input validation
    if args.config_file:
        if not os.path.exists(args.config_file):
            p_inj_conf.error("Primary config file {0} does not exist!"
                             .format(args.config_file))

    if args.secondary_config_file:
        if not os.path.exists(args.secondary_config_file):
            p_inj_conf.error("Secondary config file {0} does not exist!"
                             .format(args.secondary_config_file))

    if not args.config_file and not args.secondary_config_file:
        p_inj_conf.error("No configuration files specified - nothing to do!")

    with VMContextManager(args.PACKAGE, args.output) as vm:
        platform = vm.get_platform()

        # Platform-specific input validation
        if args.config_file and not platform.CONFIG_TEXT_FILE:
            # All reference platforms support config files, but be safe...
            p_inj_conf.error("Configuration file not supported for platform {0}"
                             .format(platform.__name__))

        if (args.secondary_config_file and
            not platform.SECONDARY_CONFIG_TEXT_FILE):
            p_inj_conf.error("Secondary configuration file not supported for "
                             "platform '{0}'".format(platform.__name__))

        # Find the disk drive where the config should be injected
        drive_device = vm.find_empty_drive(platform.BOOTSTRAP_DISK_TYPE)
        if drive_device is None:
            raise LookupError("Could not find an empty {0} drive to "
                              "inject the config into"
                              .format(platform.BOOTSTRAP_DISK_TYPE))
        (cont_type, drive_address) = vm.find_device_location(drive_device)

        # Copy config file(s) to per-platform name in working directory
        config_files = []
        if args.config_file:
            dest = os.path.join(vm.working_dir, platform.CONFIG_TEXT_FILE)
            shutil.copy(args.config_file, dest)
            config_files.append(dest)
        if args.secondary_config_file:
            dest = os.path.join(vm.working_dir,
                                platform.SECONDARY_CONFIG_TEXT_FILE)
            shutil.copy(args.secondary_config_file, dest)
            config_files.append(dest)

        # Package the config files into a disk image
        if platform.BOOTSTRAP_DISK_TYPE == 'cdrom':
            bootstrap_file = os.path.join(vm.working_dir, 'config.iso')
            create_disk_image(bootstrap_file, contents=config_files)
        elif platform.BOOTSTRAP_DISK_TYPE == 'harddisk':
            bootstrap_file = os.path.join(vm.working_dir, 'config.img')
            create_disk_image(bootstrap_file, file_format='raw',
                              contents=config_files)
        else:
            raise ValueUnsupportedError("bootstrap disk type",
                                        platform.BOOTSTRAP_DISK_TYPE,
                                        "'cdrom' or 'harddisk'")

        # Inject the disk image into the OVA, using "add-disk" functionality
        new_args = argparse.Namespace(
            DISK_IMAGE=bootstrap_file,
            type=platform.BOOTSTRAP_DISK_TYPE,
            file_id=None,
            controller=cont_type,
            address=drive_address,
            subtype=None,
            description='Configuration disk',
            diskname=None,
            force=True,
            )
        add_disk_worker(vm, new_args)


p_inj_conf = subparsers.add_parser(
    'inject-config',
    help="Inject a configuration file into an OVF package",
    usage=("""
  {0} inject-config --help
  {0} [-f] [-v] inject-config PACKAGE -c CONFIG_FILE [-o OUTPUT]
  {0} [-f] [-v] inject-config PACKAGE -s SECONDARY_CONFIG_FILE [-o OUTPUT]
  {0} [-f] [-v] inject-config PACKAGE -c CONFIG_FILE
                              -s SECONDARY_CONFIG_FILE [-o OUTPUT]"""
           .format(os.path.basename(sys.argv[0]))),
    description="""
Add one or more "bootstrap" configuration file(s) to the given OVF or OVA.""")
subparser_lookup['inject-config'] = p_inj_conf

p_inj_conf.add_argument('-o', '--output',
                        help="""Name/path of new VM package to create instead
of updating the existing package""")

p_inj_conf.add_argument('-c', '--config-file',
                        help="""Primary configuration text file to embed""")
p_inj_conf.add_argument('-s', '--secondary-config-file',
                        help="""Secondary configuration text file to embed """
                        """(currently only supported in IOS XRv for """
                        """admin config)""")
p_inj_conf.add_argument('PACKAGE',
                        help="""Package, OVF descriptor or OVA file to edit""")
p_inj_conf.set_defaults(func=inject_config)
