#!/usr/bin/env python
#
# add_file.py - Implements "cot add-file" command
#
# October 2013, Glenn F. Matthews
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

import os.path
import logging
import sys

from .vm_context_manager import VMContextManager
from .data_validation import check_for_conflict, InvalidInputError

logger = logging.getLogger(__name__)

def add_file(UI,
             FILE,
             PACKAGE,
             output=None,
             file_id=None,
             **kwargs):
    """Add a file (such as a README) to the package.
    """

    if not os.path.exists(FILE):
        raise InvalidInputError("Specified file {0} does not exist!"
                                .format(FILE))

    with VMContextManager(PACKAGE, output) as vm:
        filename = os.path.basename(FILE)
        (file, _, _, _) = vm.search_from_filename(filename)
        if file_id is not None:
            (f2, _, _, _) = vm.search_from_file_id(file_id)
            file = check_for_conflict("File to overwrite", [file, f2])
        if file_id is None:
            if file is not None:
                file_id = vm.get_id_from_file(file)
            else:
                file_id = filename

        if file is not None:
            UI.confirm_or_die("Replace existing file {0} with {1}?"
                              .format(vm.get_path_from_file(file),
                                      FILE))
            logger.warning("Overwriting existing File in VM")

        vm.add_file(FILE, file_id, file)

def create_subparser(parent):
    p = parent.add_parser(
        'add-file',
        usage=("""
  {0} add-file --help
  {0} [-f] [-v] add-file FILE PACKAGE [-o OUTPUT] [-f FILE_ID]"""
               .format(os.path.basename(sys.argv[0]))),
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
    p.set_defaults(func=add_file)
    return 'add-file', p

