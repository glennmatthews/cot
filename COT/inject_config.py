#!/usr/bin/env python
#
# inject_config.py - Implements "cot inject-config" command
#
# February 2014, Glenn F. Matthews
# Copyright (c) 2014-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Implements "inject-config" command."""

import logging
import os.path
import shutil

from .add_disk import add_disk_worker
from .data_validation import ValueUnsupportedError, InvalidInputError
from COT.helpers import create_disk_image
from .submodule import COTSubmodule

logger = logging.getLogger(__name__)


class COTInjectConfig(COTSubmodule):
    """Wrap configuration file(s) into a disk image embedded into the VM.

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`,
    :attr:`~COTSubmodule.package`,
    :attr:`~COTSubmodule.output`

    Attributes:
    :attr:`config_file`,
    :attr:`secondary_config_file`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTInjectConfig, self).__init__(UI)
        self._config_file = None
        self._secondary_config_file = None

    @property
    def config_file(self):
        """Primary configuration file.

        :raise InvalidInputError: if the file does not exist
        :raise InvalidInputError: if the `platform described by
          :attr:`package` doesn't support configuration files.
        """
        return self._config_file

    @config_file.setter
    def config_file(self, value):
        value = str(value)
        if not os.path.exists(value):
            raise InvalidInputError("Primary config file {0} does not exist!"
                                    .format(value))
        if not self.vm.platform.CONFIG_TEXT_FILE:
            raise InvalidInputError(
                "Configuration file not supported for platform {0}"
                .format(self.vm.platform.__name__))
        self._config_file = value

    @property
    def secondary_config_file(self):
        """Secondary configuration file.

        :raise InvalidInputError: if the file does not exist
        :raise InvalidInputError: if the platform described by
          :attr:`package` doesn't support secondary configuration files.
        """
        return self._secondary_config_file

    @secondary_config_file.setter
    def secondary_config_file(self, value):
        value = str(value)
        if not os.path.exists(value):
            raise InvalidInputError("Secondary config file {0} does not exist!"
                                    .format(value))
        if not self.vm.platform.SECONDARY_CONFIG_TEXT_FILE:
            raise InvalidInputError(
                "Secondary configuration file not supported for platform {0}"
                .format(self.vm.platform.__name__))
        self._secondary_config_file = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        # Need some work to do!
        work_to_do = False
        if self.config_file is not None:
            work_to_do = True
        elif self.secondary_config_file is not None:
            work_to_do = True

        if not work_to_do:
            return False, "No configuration files specified - nothing to do!"
        return super(COTInjectConfig, self).ready_to_run()

    def run(self):
        """Do the actual work of this submodule.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTInjectConfig, self).run()

        vm = self.vm

        platform = vm.platform

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
        if self.config_file:
            dest = os.path.join(vm.working_dir, platform.CONFIG_TEXT_FILE)
            shutil.copy(self.config_file, dest)
            config_files.append(dest)
        if self.secondary_config_file:
            dest = os.path.join(vm.working_dir,
                                platform.SECONDARY_CONFIG_TEXT_FILE)
            shutil.copy(self.secondary_config_file, dest)
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

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        :param object parent: Subparser grouping object returned by
            :meth:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
        p = parent.add_parser(
            'inject-config',
            help="Inject a configuration file into an OVF package",
            usage=self.UI.fill_usage("inject-config", [
                "PACKAGE -c CONFIG_FILE [-o OUTPUT]",
                "PACKAGE -s SECONDARY_CONFIG_FILE [-o OUTPUT]",
                "PACKAGE -c CONFIG_FILE -s SECONDARY_CONFIG_FILE [-o OUTPUT]",
            ]),
            description="""Add one or more "bootstrap" configuration """
            """file(s) to the given OVF or OVA.""")

        p.add_argument('-o', '--output',
                       help="""Name/path of new VM package to create """
                       """instead of updating the existing package""")

        p.add_argument('-c', '--config-file',
                       help="""Primary configuration text file to embed""")
        p.add_argument('-s', '--secondary-config-file',
                       help="""Secondary configuration text file to embed """
                       """(currently only supported in IOS XRv for """
                       """admin config)""")
        p.add_argument('PACKAGE',
                       help="""Package, OVF descriptor or OVA file to edit""")
        p.set_defaults(instance=self)

        storage['inject-config'] = p
