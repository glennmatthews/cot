#!/usr/bin/env python
#
# remove_file.py - Implements "cot remove-file" command
#
# June 2016, Glenn F. Matthews
# Copyright (c) 2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Module for removing files from VM definitions.

.. autosummary::
  COTRemoveFile
"""

import logging

from .submodule import COTSubmodule
from .data_validation import check_for_conflict, InvalidInputError

logger = logging.getLogger(__name__)


class COTRemoveFile(COTSubmodule):
    """Remove a file (such as a README) from the package.

    Inherited attributes:

    :attr:`~COTGenericSubmodule.UI`,
    :attr:`~COTSubmodule.package`,
    :attr:`~COTSubmodule.output`

    Attributes:
    :attr:`file_path`,
    :attr:`file_id`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTRemoveFile, self).__init__(UI)
        self.file_path = None
        """File name or path to be removed from the package."""
        self.file_id = None
        """File identifier to be removed from the package."""

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.file_path is None and self.file_id is None:
            return False, "No file information provided!"
        return super(COTRemoveFile, self).ready_to_run()

    def run(self):
        """Do the actual work of this submodule.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTRemoveFile, self).run()

        vm = self.vm

        # Find the existing file entry.
        # There may also be a disk entry for this file.
        # There may also be a disk device that maps this file to a drive.
        (file1, disk1, _, disk_dev1) = vm.search_from_filename(self.file_path)
        (file2, disk2, _, disk_dev2) = vm.search_from_file_id(self.file_id)
        file = check_for_conflict("file to remove", [file1, file2])
        disk = check_for_conflict("disk associated with file to remove",
                                  [disk1, disk2])
        disk_drive = check_for_conflict("disk drive mapping this file",
                                        [disk_dev1, disk_dev2])

        if file is None:
            raise InvalidInputError("No such file found")

        if self.file_id is None:
            self.file_id = vm.get_id_from_file(file)
        if self.file_path is None:
            self.file_path = vm.get_path_from_file(file)

        prompt_info = "file '{0}' (ID '{1}')".format(self.file_path,
                                                     self.file_id)
        if disk is not None:
            prompt_info += " and disk '{0}'".format(vm.get_id_from_disk(disk))
        if disk_drive is not None:
            prompt_info += " and device '{0}'".format(
                vm.device_info_str(disk_drive))

        self.UI.confirm_or_die("Remove {0}?".format(prompt_info))

        vm.remove_file(file, disk=disk,
                       disk_drive=disk_drive)

    def create_subparser(self):
        """Create 'remove-file' CLI subparser."""
        p = self.UI.add_subparser(
            'remove-file',
            aliases=['delete-file'],
            add_help=False,
            usage=self.UI.fill_usage("remove-file", [
                "[-f FILE_PATH] [-i FILE_ID] PACKAGE [-o OUTPUT]",
            ]),
            help="Remove a file from an OVF package",
            description="""
Remove a file from the given OVF. Will prompt for confirmation unless
--force is set.""")

        group = p.add_argument_group("general options")

        group.add_argument('-h', '--help', action='help',
                           help="""Show this help message and exit""")
        group.add_argument('-o', '--output',
                           help="""Name/path of new OVF/OVA package to """
                           """create instead of updating the existing OVF""")

        group = p.add_argument_group("file selection options")

        group.add_argument('-f', '--file-path',
                           help="""File name or path within the package""")
        group.add_argument('-i', '--file-id',
                           help="""File ID string within the package""")

        p.add_argument('PACKAGE',
                       help="""Package, OVF descriptor or OVA file to edit""")
        p.set_defaults(instance=self)
