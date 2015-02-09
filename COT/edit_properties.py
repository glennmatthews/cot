#!/usr/bin/env python
#
# edit_properties.py - Implements "edit-properties" sub-command
#
# August 2013, Glenn F. Matthews
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

import logging
import os.path
import textwrap

from .submodule import COTSubmodule
from .data_validation import ValueUnsupportedError

logger = logging.getLogger(__name__)


class COTEditProperties(COTSubmodule):

    def __init__(self, UI):
        super(COTEditProperties, self).__init__(
            UI,
            [
                "PACKAGE",
                "output",
                "config_file",
                "properties"
            ])

    def validate_arg(self, arg, value):
        """Check whether it's OK to set the given argument to the given value.
        Returns either (True, massaged_value) or (False, reason)"""

        valid, value_or_reason = super(COTEditProperties, self).validate_arg(
            arg, value)
        if not valid or value_or_reason is None:
            return valid, value_or_reason
        value = value_or_reason

        if arg == "config_file":
            if not os.path.exists(value):
                return False, ("Specified config file {0} does not exist!"
                               .format(value))
        elif arg == "properties":
            for key_value_pair in value:
                try:
                    (k, v) = key_value_pair.split('=', 1)
                    logger.debug("key: {0} value: {1}".format(k, v))
                    if k == '':
                        raise ValueError()
                except ValueError:
                    return False, ("Invalid property '{0}' - properties "
                                   "must be in 'key=value' form"
                                   .format(key_value_pair))

        return valid, value_or_reason

    def set_value(self, arg, value):
        super(COTEditProperties, self).set_value(arg, value)
        if arg == "properties" and value is not None:
            self.args[arg] = value

    def ready_to_run(self):
        """Are we ready to go?
        Returns the tuple (ready, reason)"""
        return super(COTEditProperties, self).ready_to_run()

    def run(self):
        super(COTEditProperties, self).run()

        config_file = self.get_value("config_file")
        properties = self.get_value("properties")

        vm = self.vm

        if config_file is not None:
            vm.config_file_to_properties(config_file)

        if properties is not None:
            for key_value_pair in properties:
                (key, value) = key_value_pair.split('=', 1)
                logger.debug("key: {0} value: {1}".format(key, value))
                if value == '':
                    value = self.UI.get_input(
                        "Enter value for property '{0}'",
                        value)
                curr_value = vm.get_property_value(key)
                if curr_value is None:
                    self.UI.confirm_or_die(
                        "Property '{0}' does not yet exist.\n"
                        "Create it?".format(key))
                    # TODO - for new property, prompt for label/descr/type?
                vm.set_property_value(key, value)

        if config_file is None and properties is None:
            # Interactive mode!
            self.edit_properties_interactive(vm)

    def edit_properties_interactive(self, vm):
        wrapper = textwrap.TextWrapper(initial_indent='',
                                       subsequent_indent='                 ')
        format_str = '{0:15} "{1}"'
        pa = vm.get_property_array()
        while True:
            print("")
            print("Please choose a property to edit:")
            i = 1
            for p in pa:
                print("""{i:4d}) {label:40} ({key})"""
                      .format(i=i, label='"'+p['label']+'"', key=p['key']))
                i += 1

            input = self.UI.get_input("""Enter property number to edit, """
                                      """or "q" to quit and write changes""",
                                      default_value="q")

            if input is None or input == 'q' or input == 'Q':
                break
            input = int(input)
            if input <= 0 or input > len(pa):
                continue

            print("")
            p = pa[input-1]
            key = p['key']
            old_value = p['value']
            print(wrapper.fill(format_str.format("Key:", p['key'])))
            print(wrapper.fill(format_str.format("Label:", p['label'])))
            print(wrapper.fill(format_str.format("Description:",
                                                 p['description'])))
            print(wrapper.fill(format_str.format("Type:", p['type'])))
            print(wrapper.fill(format_str.format("Qualifiers:",
                                                 p['qualifiers'])))
            print(wrapper.fill(format_str.format("Current Value:", old_value)))
            print("")

            while True:
                new_value = self.UI.get_input("New value for this property",
                                              default_value=old_value)
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

    def create_subparser(self, parent):
        p = parent.add_parser(
            'edit-properties', add_help=False,
            help="""Edit environment properties of an OVF""",
            usage=self.UI.fill_usage("edit-properties", [
                "PACKAGE -p KEY1=VALUE1 [KEY2=VALUE2 ...] [-o OUTPUT]",
                "PACKAGE -c CONFIG_FILE [-o OUTPUT]",
                "PACKAGE [-o OUTPUT]",
            ]),
            description="""
Configure environment properties of the given OVF or OVA. The user may specify
key-value pairs as command-line arguments or may provide a config-file to
read from. If neither are specified, the program will run interactively.""")

        p.add_argument('PACKAGE',
                       help="""OVF descriptor or OVA file to edit""")

        g = p.add_argument_group("general options")

        g.add_argument('-h', '--help', action='help',
                       help="""Show this help message and exit""")
        g.add_argument('-o', '--output',
                       help="Name/path of new OVF/OVA package to create "
                       "instead of updating the existing OVF")

        g = p.add_argument_group("property setting options")

        g.add_argument('-c', '--config-file',
                       help="Read configuration CLI from this text file and "
                       "generate generic properties for each line of CLI")
        g.add_argument('-p', '--properties', action='append', nargs='+',
                       metavar=('KEY1=VALUE1', 'KEY2=VALUE2'),
                       help="Set the given property key-value pair(s). "
                       "This argument may be repeated as needed to specify "
                       "multiple properties to edit.")

        p.set_defaults(instance=self)

        return 'edit-properties', p
