#!/usr/bin/env python
#
# edit_product.py - Implements "edit-product" sub-command
#
# August 2013, Glenn F. Matthews
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

import logging
import os.path
import sys

from .cli import subparsers, subparser_lookup
from .vm_context_manager import VMContextManager

logger = logging.getLogger('cot')

def edit_product(args):
    """Edit product information (short version, long version)"""
    if args.version is None and args.full_version is None:
        p_edit_prod.error("Neither --version nor --full-version was "
                          "specified - nothing to do!")

    with VMContextManager(args.PACKAGE, args.output) as vm:
        if args.version is not None:
            vm.set_short_version(args.version)
        if args.full_version is not None:
            vm.set_long_version(args.full_version)


# Add ourselves to the parser options
p_edit_prod = subparsers.add_parser(
    'edit-product',
    help="""Edit product info in an OVF""",
    usage=("""
  {0} edit-product --help
  {0} [-f] [-v] edit-product PACKAGE [-o OUTPUT]
                             [-v SHORT_VERSION] [-V FULL_VERSION]"""
           .format(os.path.basename(sys.argv[0]))),
    description="""
Edit product information attributes of the given OVF or OVA""")
subparser_lookup['edit-product'] = p_edit_prod

p_edit_prod.add_argument('-o', '--output',
                         help="""Name/path of new OVF/OVA package to create
                                 instead of updating the existing OVF""")
p_edit_prod.add_argument('-v', '--version', metavar="SHORT_VERSION",
                         help="""Software short version string, such as
                                 "15.3(4)S" or "5.2.0.01I" """)
p_edit_prod.add_argument('-V', '--full-version',
                         help="""Software long version string, such as "Cisco
                                 IOS-XE Software, Version 15.3(4)S" """)
p_edit_prod.add_argument('PACKAGE',
                         help="""OVF descriptor or OVA file to edit""")
p_edit_prod.set_defaults(func=edit_product)
