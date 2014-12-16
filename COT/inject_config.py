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
from .data_validation import ValueUnsupportedError, InvalidInputError
from .helper_tools import create_disk_image
from .submodule import COTSubmodule

logger = logging.getLogger(__name__)

class COTInjectConfig(COTSubmodule):
    """Wrap the given configuration file(s) into an appropriate disk image file
    and embed it into the given VM package.
    """

    def __init__(self, UI):
        super(COTInjectConfig, self).__init__(
            UI,
            [
                "PACKAGE",
                "output",
                "config_file",
                "secondary_config_file",
            ])


    def validate_arg(self, arg, value):
        """Check whether it's OK to set the given argument to the given value.
        Returns either (True, massaged_value) or (False, reason)"""
        valid, value_or_reason = super(COTInjectConfig, self).validate_arg(
            arg, value)
        if not valid or value_or_reason is None:
            return valid, value_or_reason
        value = value_or_reason

        if arg == "config_file":
            if not os.path.exists(value):
                return False, ("Primary config file {0} does not exist!"
                               .format(value))
        elif arg == "secondary_config_file":
            if not os.path.exists(value):
                return False, ("Secondary config file {0} does not exist!"
                               .format(value))

        return valid, value_or_reason


    def ready_to_run(self):
        """Are we ready to go?
        Returns the tuple (ready, reason)"""

        # Need some work to do!
        work_to_do = False
        if self.get_value("config_file") is not None:
            work_to_do = True
        elif self.get_value("secondary_config_file") is not None:
            work_to_do = True

        if not work_to_do:
            return False, "No configuration files specified - nothing to do!"
        return super(COTInjectConfig, self).ready_to_run()


    def run(self):
        super(COTInjectConfig, self).run()

        with self.vm as vm:
            platform = vm.get_platform()

            config_file = self.get_value("config_file")
            secondary_config_file = self.get_value("secondary_config_file")
            # Platform-specific input validation - TODO move to validate_input
            if config_file and not platform.CONFIG_TEXT_FILE:
                # All reference platforms support config files, but be safe...
                raise InvalidInputError(
                    "Configuration file not supported for platform {0}"
                    .format(platform.__name__))

            if (secondary_config_file and
                not platform.SECONDARY_CONFIG_TEXT_FILE):
                raise InvalidInputError(
                    "Secondary configuration file not supported for "
                    "platform '{0}'".format(platform.__name__))

            # Find the disk drive where the config should be injected
            # First, look for any previously-injected config disk to overwrite:
            if platform.BOOTSTRAP_DISK_TYPE == 'cdrom':
                (f, d, ci, drive_device) = vm.search_from_filename('config.iso')
            elif platform.BOOTSTRAP_DISK_TYPE == 'harddisk':
                (f, d, ci, drive_device) = vm.search_from_filename('config.vmdk')
            else:
                raise ValueUnsupportedError("bootstrap disk type",
                                            platform.BOOTSTRAP_DISK_TYPE,
                                            "'cdrom' or 'harddisk'")
            if f is not None:
                file_id = vm.get_id_from_file(f)
                self.UI.confirm_or_die(
                    "Existing configuration disk '{0}' found.\n"
                    "Continue and overwrite it?".format(file_id))
                logger.warning("Overwriting existing config disk '{0}'"
                               .format(file_id))
            else:
                file_id = None
                # Find the empty slot where we should inject the config
                drive_device = vm.find_empty_drive(platform.BOOTSTRAP_DISK_TYPE)

            if drive_device is None:
                raise LookupError("Could not find an empty {0} drive to "
                                  "inject the config into"
                                  .format(platform.BOOTSTRAP_DISK_TYPE))
            (cont_type, drive_address) = vm.find_device_location(drive_device)

            # Copy config file(s) to per-platform name in working directory
            config_files = []
            if config_file:
                dest = os.path.join(vm.working_dir, platform.CONFIG_TEXT_FILE)
                shutil.copy(config_file, dest)
                config_files.append(dest)
            if secondary_config_file:
                dest = os.path.join(vm.working_dir,
                                    platform.SECONDARY_CONFIG_TEXT_FILE)
                shutil.copy(secondary_config_file, dest)
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
            add_disk_worker(
                UI=self.UI,
                vm=vm,
                DISK_IMAGE=bootstrap_file,
                type=platform.BOOTSTRAP_DISK_TYPE,
                file_id=file_id,
                controller=cont_type,
                address=drive_address,
                subtype=None,
                description='Configuration disk',
                diskname=None,
            )


    def create_subparser(self, parent):
        p = parent.add_parser(
            'inject-config',
            help="Inject a configuration file into an OVF package",
            usage=("""
  {0} inject-config --help
  {0} [-f] [-v] inject-config PACKAGE -c CONFIG_FILE [-o OUTPUT]
  {0} [-f] [-v] inject-config PACKAGE -s SECONDARY_CONFIG_FILE [-o OUTPUT]
  {0} [-f] [-v] inject-config PACKAGE -c CONFIG_FILE
                              -s SECONDARY_CONFIG_FILE [-o OUTPUT]"""
                   .format(os.path.basename(sys.argv[0]))),
            description="""Add one or more "bootstrap" configuration file(s) """
            """to the given OVF or OVA.""")

        p.add_argument('-o', '--output',
                       help="""Name/path of new VM package to create instead """
                       """of updating the existing package""")

        p.add_argument('-c', '--config-file',
                       help="""Primary configuration text file to embed""")
        p.add_argument('-s', '--secondary-config-file',
                       help="""Secondary configuration text file to embed """
                       """(currently only supported in IOS XRv for """
                       """admin config)""")
        p.add_argument('PACKAGE',
                       help="""Package, OVF descriptor or OVA file to edit""")
        p.set_defaults(func=self.run)
        p.set_defaults(instance=self)

        return 'inject-config', p
