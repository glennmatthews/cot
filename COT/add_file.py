#!/usr/bin/env python
#
# add_file.py - Implements "cot add-file" command
#
# October 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

import os.path
import logging
import sys

from .cli import subparsers, subparser_lookup, confirm_or_die
from .vm_context_manager import VMContextManager
from .data_validation import check_for_conflict

logger = logging.getLogger('cot')

def add_file(args):
    """Add a file (such as a README) to the package.
    """

    if not os.path.exists(args.FILE):
        p_add_file.error("Specified file {0} does not exist!"
                         .format(args.FILE))

    with VMContextManager(args.PACKAGE, args.output) as vm:
        filename = os.path.basename(args.FILE)
        (file, _, _, _) = vm.search_from_filename(filename)
        if args.file_id is not None:
            (f2, _, _, _) = vm.search_from_file_id(args.file_id)
            file = check_for_conflict("File to overwrite", [file, f2])
        if args.file_id is None:
            if file is not None:
                args.file_id = vm.get_id_from_file(file)
            else:
                args.file_id = filename

        if file is not None:
            confirm_or_die("Replace existing file {0} with {1}?"
                           .format(vm.get_path_from_file(file),
                                   args.FILE),
                           args.force)
            logger.warning("Overwriting existing File in VM")

        vm.add_file(args.FILE, args.file_id, file)


p_add_file = subparsers.add_parser(
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
subparser_lookup['add-file'] = p_add_file

p_add_file.add_argument('-o', '--output',
                        help="""Name/path of new VM package to create
                              instead of updating the existing package""")
p_add_file.add_argument('-f', '--file-id',
                        help="""File ID string within the package
                               (default: same as filename)""")
p_add_file.add_argument('FILE',
                        help="""File to add to the package""")
p_add_file.add_argument('PACKAGE',
                        help="""Package, OVF descriptor or OVA file to edit""")
p_add_file.set_defaults(func=add_file)
