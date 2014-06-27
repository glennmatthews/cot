#!/usr/bin/env python
#
# info.py - Implements "info" sub-command
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

import logging
import os.path
import sys

from .cli import subparsers, subparser_lookup
from .vm_context_manager import VMContextManager

logger = logging.getLogger('cot')

def info(args):
    """Display VM information string"""
    for package in args.PACKAGE_LIST:
        with VMContextManager(package, None) as vm:
            print(vm.info_string(args.verbosity))


# Add ourselves to the parser options
p_info = subparsers.add_parser(
    'info',
    help="""Generate a description of an OVF package""",
    usage=("""
  {0} info --help
  {0} info [-b | -v] PACKAGE [PACKAGE ...]"""
           .format(os.path.basename(sys.argv[0]))),
    description="""
Show a summary of the contents of the given OVF(s) and/or OVA(s).""")
subparser_lookup['info'] = p_info

verbosity_group = p_info.add_mutually_exclusive_group()

verbosity_group.add_argument('-b', '--brief',
                             action='store_const', const='brief',
                             dest='verbosity',
                             help="""Brief output (shorter)""")
verbosity_group.add_argument('-v', '--verbose',
                             action='store_const', const='verbose',
                             dest='verbosity',
                             help="""Verbose output (longer)""")

p_info.add_argument('PACKAGE_LIST',
                    nargs='+',
                    metavar='PACKAGE [PACKAGE ...]',
                    help="""OVF descriptor(s) and/or OVA file(s) to describe""")
p_info.set_defaults(func=info)
