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

from .vm_context_manager import VMContextManager
from .data_validation import InvalidInputError

logger = logging.getLogger(__name__)

def edit_product(PACKAGE=None,
                 output=None,
                 version=None,
                 full_version=None,
                 **kwargs):
    """Edit product information (short version, long version)"""
    if version is None and full_version is None:
        raise InvalidInputError("Neither --version nor --full-version was "
                                "specified - nothing to do!")

    with VMContextManager(PACKAGE, output) as vm:
        if version is not None:
            vm.set_short_version(version)
        if full_version is not None:
            vm.set_long_version(full_version)


def create_subparser(parent):
    p = parent.add_parser(
        'edit-product',
        help="""Edit product info in an OVF""",
        usage=("""
  {0} edit-product --help
  {0} [-f] [-v] edit-product PACKAGE [-o OUTPUT]
                             [-v SHORT_VERSION] [-V FULL_VERSION]"""
               .format(os.path.basename(sys.argv[0]))),
        description="""
Edit product information attributes of the given OVF or OVA""")

    p.add_argument('-o', '--output',
                   help="""Name/path of new OVF/OVA package to create """
                   """instead of updating the existing OVF""")
    p.add_argument('-v', '--version', metavar="SHORT_VERSION",
                   help="""Software short version string, such as """
                   """"15.3(4)S" or "5.2.0.01I" """)
    p.add_argument('-V', '--full-version',
                   help="""Software long version string, such as """
                   """"Cisco IOS-XE Software, Version 15.3(4)S" """)
    p.add_argument('PACKAGE',
                   help="""OVF descriptor or OVA file to edit""")
    p.set_defaults(func=edit_product)

    return 'edit-product', p
