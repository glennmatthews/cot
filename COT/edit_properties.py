#!/usr/bin/env python
#
# edit_properties.py - Implements "edit-properties" sub-command
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

import logging
import os.path
import sys
import textwrap

from .cli import subparsers, subparser_lookup, confirm_or_die, get_input
from .vm_context_manager import VMContextManager
from .data_validation import ValueUnsupportedError

logger = logging.getLogger('cot')

def edit_properties(args):
    """Edit environment properties in an OVF descriptor.
    """

    with VMContextManager(args.PACKAGE, args.output) as vm:
        if args.config_file is not None:
            if not os.path.exists(args.config_file):
                p_edit_prop.error("Specified config file {0} does not exist!"
                                  .format(args.config_file))
            vm.config_file_to_properties(args.config_file)

        if args.properties is not None:
            for key_value_pair in args.properties:
                try:
                    (key, value) = key_value_pair.split('=',1)
                    logger.debug("key: {0} value: {1}".format(key, value))
                    if key == '':
                        raise ValueError()
                except ValueError:
                    p_edit_prop.error("Invalid property '{0}' - properties "
                                      "must be in 'key=value' form"
                                      .format(key_value_pair))
                if value == '':
                    value = get_input("Enter value for property '{0}'",
                                      value, args.force)
                curr_value = vm.get_property_value(key)
                if curr_value is None:
                    confirm_or_die("Property '{0}' does not yet exist.\n"
                                   "Create it?"
                                   .format(key), args.force)
                    # TODO - for new property, prompt for label/descr/type?
                vm.set_property_value(key, value)

        if args.config_file is None and args.properties is None:
            # Interactive mode!
            edit_properties_interactive(args, vm)


def edit_properties_interactive(args, vm):
    wrapper = textwrap.TextWrapper(initial_indent='',
                                   subsequent_indent='                 ')
    format_str = '{0:15} "{1}"'
    keys = vm.get_property_keys()
    while True:
        print("")
        print("Please choose a property to edit:")
        i = 1
        for key in keys:
            label = vm.get_property_label(key)
            print("""{i:4d}) {label:40} ({key})"""
                  .format(i=i, label='"'+label+'"', key=key))
            i += 1

        input = get_input("""Enter property number to edit, """
                          """or "q" to quit and write changes""",
                          default="q")

        if input is None or input == 'q' or input == 'Q':
            break
        input = int(input)
        if input <= 0 or input > len(keys):
            continue

        print("")
        key = keys[input-1]
        old_value = vm.get_property_value(key)
        print(wrapper.fill(format_str.format("Key:", key)))
        print(wrapper.fill(format_str.format("Label:",
                                             vm.get_property_label(key))))
        print(wrapper.fill(format_str.format("Description:",
                                             vm.get_property_description(key))))
        print(wrapper.fill(format_str.format("Type:",
                                             vm.get_property_type(key))))
        print(wrapper.fill(format_str.format("Qualifiers:",
                                             vm.get_property_qualifiers(key))))
        print(wrapper.fill(format_str.format("Current Value:", old_value)))
        print("")

        while True:
            new_value = get_input("""New value for this property""",
                                  default=old_value)
            if new_value == old_value:
                print("(no change)")
                break
            else:
                try:
                    new_value = vm.set_property_value(key, new_value)

                    print("""Successfully set the value of """
                          """property "{0}" to "{1}" """
                          .format(key, new_value))
                    break
                except ValueUnsupportedError as e:
                    print(e)
            print("")


p_edit_prop = subparsers.add_parser(
    'edit-properties', add_help=False,
    help="""Edit environment properties of an OVF""",
    usage=("""
  {0} edit-properties --help
  {0} [-f] [-v] edit-properties PACKAGE -p KEY1=VALUE1 [KEY2=VALUE2 ...]
                                [-o OUTPUT]
  {0} [-f] [-v] edit-properties PACKAGE -c CONFIG_FILE [-o OUTPUT]
  {0} [-f] [-v] edit-properties PACKAGE [-o OUTPUT]"""
           .format(os.path.basename(sys.argv[0]))),
    description="""
Configure environment properties of the given OVF or OVA. The user may specify
key-value pairs as command-line arguments or may provide a config-file to
read from. If neither are specified, the program will run interactively.""")
subparser_lookup['edit-properties'] = p_edit_prop

p_edit_prop.add_argument('PACKAGE',
                         help="""OVF descriptor or OVA file to edit""")

p_epp_gen = p_edit_prop.add_argument_group("general options")

p_epp_gen.add_argument('-h', '--help', action='help',
                       help="""Show this help message and exit""")
p_epp_gen.add_argument('-o', '--output',
                       help="""Name/path of new OVF/OVA package to create
                               instead of updating the existing OVF""")

p_epp_conf = p_edit_prop.add_argument_group("property setting options")

p_epp_conf.add_argument('-c', '--config-file',
                        help="""Read configuration CLI from this text file
                                and generate generic properties for each
                                line of CLI""")
p_epp_conf.add_argument('-p','--properties',
                        nargs='+',
                        metavar=('KEY1=VALUE1', 'KEY2=VALUE2'),
                        help="""Set the given property key-value pairs""")

p_edit_prop.set_defaults(func=edit_properties)
