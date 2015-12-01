#!/usr/bin/env python
#
# add_file.py - Implements "cot add-file" command
#
# October 2013, Glenn F. Matthews
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

"""Module for adding files to VM definitions.

.. autosummary::
  COTAddFile
"""

import os.path
import logging

from .data_validation import check_for_conflict, InvalidInputError
from .submodule import COTSubmodule

logger = logging.getLogger(__name__)


class COTAddFile(COTSubmodule):
    """Add a file (such as a README) to the package.

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`,
    :attr:`~COTSubmodule.package`,
    :attr:`~COTSubmodule.output`

    Attributes:
    :attr:`file`,
    :attr:`file_id`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTAddFile, self).__init__(UI)
        self._file = None
        self.file_id = None
        """File identifier string."""

    @property
    def file(self):
        """File to be added to the package.

        :raises: :exc:`.InvalidInputError` if the file does not exist.
        """
        return self._file

    @file.setter
    def file(self, value):
        if not os.path.exists(value):
            raise InvalidInputError("Specified file '{0}' does not exist!"
                                    .format(value))
        self._file = value

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.file is None:
            return False, "FILE is a mandatory argument!"
        return super(COTAddFile, self).ready_to_run()

    def run(self):
        """Do the actual work of this submodule.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTAddFile, self).run()

        vm = self.vm

        filename = os.path.basename(self.file)
        (file, _, _, _) = vm.search_from_filename(filename)
        if self.file_id is not None:
            (f2, _, _, _) = vm.search_from_file_id(self.file_id)
            file = check_for_conflict("File to overwrite", [file, f2])
        if self.file_id is None:
            if file is not None:
                self.file_id = vm.get_id_from_file(file)
            else:
                self.file_id = filename

        if file is not None:
            self.UI.confirm_or_die("Replace existing file {0} with {1}?"
                                   .format(vm.get_path_from_file(file),
                                           self.file))
            logger.warning("Overwriting existing File in OVF")

        vm.add_file(self.file, self.file_id, file)

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        :param object parent: Subparser grouping object returned by
            :meth:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
        p = parent.add_parser(
            'add-file',
            usage=self.UI.fill_usage("add-file", [
                "FILE PACKAGE [-o OUTPUT] [-f FILE_ID]",
            ]),
            help="Add a file to an OVF package",
            description="""
Add or replace a file in the given OVF. If the specified file
and/or file-id match existing package contents, will replace it
(prompting for confirmation if --force was not set); otherwise, will
create a new file entry.""")

        p.add_argument('-o', '--output',
                       help="""Name/path of new VM package to create """
                       """instead of updating the existing package""")
        p.add_argument('-f', '--file-id',
                       help="""File ID string within the package """
                       """(default: same as filename)""")
        p.add_argument('FILE', help="""File to add to the package""")
        p.add_argument('PACKAGE',
                       help="""Package, OVF descriptor or OVA file to edit""")
        p.set_defaults(instance=self)

        storage['add-file'] = p
