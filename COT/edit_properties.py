#!/usr/bin/env python
#
# edit_properties.py - Implements "edit-properties" sub-command
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Module for managing VM environment configuration properties.

**Classes**

.. autosummary::
  :nosignatures:

  COTEditProperties
"""

import argparse
import logging
import os.path
import re
import textwrap

from .submodule import COTSubmodule
from .data_validation import (
    truth_value, ValueUnsupportedError, InvalidInputError
)

logger = logging.getLogger(__name__)


class COTEditProperties(COTSubmodule):
    """Edit OVF environment XML properties.

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`,
    :attr:`~COTSubmodule.package`,
    :attr:`~COTSubmodule.output`

    Attributes:
    :attr:`config_file`,
    :attr:`properties`,
    :attr:`transports`,
    :attr:`user_configurable`
    """

    def __init__(self, ui):
        """Instantiate this submodule with the given UI."""
        super(COTEditProperties, self).__init__(ui)
        self._config_file = None
        self._properties = {}
        self._transports = None
        self.user_configurable = None
        """Value to set the user_configurable flag on properties we edit."""

    @property
    def config_file(self):
        """Path to plaintext file to read configuration lines from.

        :raise: :exc:`InvalidInputError` if the file does not exist.
        """
        return self._config_file

    @config_file.setter
    def config_file(self, value):
        if not os.path.exists(value):
            raise InvalidInputError("Specified config file {0} does not exist!"
                                    .format(value))
        self._config_file = value

    @property
    def properties(self):
        """List of property (key, value, type) tuples to update."""
        return self._properties

    @properties.setter
    def properties(self, value):
        new_value = []
        for prop in value:
            match = re.match(r"^([^=+]+?)(=[^=+]*?)?(\+[^=+]*?)?$", prop)
            if not match:
                raise InvalidInputError("Invalid property '{0}' - properties "
                                        "must be in 'key[=value][+type]' form"
                                        .format(prop))
            key = match.group(1)
            # Strip the leading '=' or '+' from these matches
            value = match.group(2)[1:] if match.group(2) else None
            prop_type = match.group(3)[1:] if match.group(3) else None

            logger.verbose("Property: key '{0}', value '{1}', type '{2}'"
                           .format(key, value, prop_type))

            new_value.append((key, value, prop_type))
        self._properties = new_value

    @property
    def transports(self):
        """Transport mechanism(s) for environment properties.."""
        return self._transports

    _KNOWN_TRANSPORTS = {
        'iso':    "iso",
        'vmware': "com.vmware.guestInfo",
        'ibm':    "http://www.ibm.com/xmlns/ovf/transport/filesystem/"
                  "etc/ovf-transport",
    }

    @transports.setter
    def transports(self, value):
        self._transports = []
        for v in value:
            if v in self._KNOWN_TRANSPORTS.keys():
                v = self._KNOWN_TRANSPORTS[v]
            if v not in self._KNOWN_TRANSPORTS.values():
                logger.warning("Unknown transport value '%s'. "
                               "You may want to contact the COT developers "
                               "to add this as a recognized value.", v)
            self._transports.append(v)

    def run(self):
        """Do the actual work of this submodule.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTEditProperties, self).run()

        if self.config_file is not None:
            self.vm.config_file_to_properties(self.config_file,
                                              self.user_configurable)

        if self.properties:
            for key, value, prop_type in self.properties:
                if value == '':
                    value = self.UI.get_input(
                        "Enter value for property '{0}'",
                        value)
                curr_value = self.vm.get_property_value(key)
                if curr_value is None:
                    self.UI.confirm_or_die(
                        "Property '{0}' does not yet exist.\n"
                        "Create it?".format(key))
                self.vm.set_property_value(
                    key, value,
                    user_configurable=self.user_configurable,
                    property_type=prop_type)

        if self.transports:
            self.vm.environment_transports = self.transports

        if (not self.config_file and not self.properties and
                not self.transports):
            logger.info("No changes specified in CLI; "
                        "entering interactive mode.")
            # Interactive mode!
            self.edit_properties_interactive()

    def edit_properties_interactive(self):
        """Present an interactive UI for the user to edit properties."""
        wrapper = textwrap.TextWrapper(initial_indent='',
                                       subsequent_indent='                 ')
        format_str = '{0:15} "{1}"'
        pa = self.vm.environment_properties
        while True:
            key_list = [p['key'] for p in pa]
            string_list = ["""{0:25} "{1}" """.format(p['key'], p['label'])
                           for p in pa]
            user_input = self.UI.choose_from_list(
                header="Please choose a property to edit:",
                option_list=key_list,
                info_list=string_list,
                footer=("Enter property key or number to edit, or "
                        "'q' to write changes and quit"),
                default_value='q')

            if user_input == 'q' or user_input == 'Q':
                break

            p = next(p for p in pa if p['key'] == user_input)

            key = p['key']
            old_value = p['value']
            prompt = "\n".join([
                wrapper.fill(format_str.format("Key:", p['key'])),
                wrapper.fill(format_str.format("Label:", p['label'])),
                wrapper.fill(format_str.format("Description:",
                                               p['description'])),
                wrapper.fill(format_str.format("Type:", p['type'])),
                wrapper.fill(format_str.format("Qualifiers:",
                                               p['qualifiers'])),
                wrapper.fill(format_str.format("Current Value:", old_value)),
                "",
                "Enter new value for this property",
            ])

            while True:
                new_value = self.UI.get_input(prompt,
                                              default_value=old_value)
                if new_value == old_value:
                    logger.info("Value for property '%s' is unchanged", key)
                    break
                else:
                    try:
                        new_value = self.vm.set_property_value(
                            key, new_value,
                            user_configurable=self.user_configurable)
                        logger.info("Successfully updated property '%s' "
                                    "value to '%s'", key, new_value)
                        # Refresh!
                        pa = self.vm.environment_properties
                        break
                    except ValueUnsupportedError as e:
                        logger.error(e)
                        continue
            continue

    def create_subparser(self):
        """Create 'edit-properties' CLI subparser."""
        p = self.UI.add_subparser(
            'edit-properties',
            aliases=['set-properties', 'edit-environment', 'set-environment'],
            add_help=False,
            help="""Edit or create environment properties of an OVF""",
            usage=self.UI.fill_usage("edit-properties", [
                "PACKAGE [-p KEY1=VALUE1 ] [-p KEY2=VALUE2 ...] "
                "[-c CONFIG_FILE] [-u [USER_CONFIGURABLE]] "
                "[-t TRANSPORT [TRANSPORT2 ...]] [-o OUTPUT]",
                "PACKAGE [-o OUTPUT]",
            ]),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
Configure environment properties of the given OVF or OVA. The user may specify
keys and values as command-line arguments or may provide a config-file to
read from. If neither --config-file, --properties, nor --transport are given,
the program will run interactively.""",
            epilog=self.UI.fill_examples([
                ("Add configuration from a text file and mark the resulting"
                 " properties as non-user-configurable.",
                 'cot edit-properties input.ovf -c config.txt -u=0'),
                ("Add/update two properties, one a string with no default"
                 " value and the other a boolean defaulting to true, and"
                 " mark both properties as user-configurable.",
                 'cot edit-properties input.ovf -p string-property+string'
                 ' -p bool-property=true+boolean --user-configurable'),
            ]),
        )

        p.add_argument('PACKAGE',
                       help="""OVF descriptor or OVA file to edit""")

        g = p.add_argument_group("general options")

        g.add_argument('-h', '--help', action='help',
                       help="""Show this help message and exit""")
        g.add_argument('-o', '--output',
                       help="Name/path of new OVF/OVA package to create "
                       "instead of updating the existing OVF")

        g = p.add_argument_group("property setting options")

        g.add_argument('-u', '--user-configurable',
                       nargs='?', const="true", type=truth_value,
                       help="Update the 'userConfigurable' flag on all "
                       "edited properties to True or the given value")

        g.add_argument('-c', '--config-file',
                       help="Read configuration CLI from this text file and "
                       "generate generic properties for each line of CLI")
        g.add_argument('-p', '--properties', action='append', nargs='+',
                       metavar=('KEY1[=VALUE1][+TYPE1]', 'K2[=V2][+T2]'),
                       help="Update or create the given property keys. "
                       "A '=' delimits the optional value to set this key to. "
                       "A '+' delimits the optional type to enforce for this "
                       "key. "
                       "This argument may be repeated as needed to specify "
                       "multiple properties to edit.")
        g.add_argument('-t', '--transports', action='append', nargs='+',
                       metavar=('TRANSPORT', 'TRANSPORT2'),
                       help="Set the transport method(s) for properties. "
                       "Known values are 'iso', 'vmware', and 'ibm', or an "
                       "arbitrary URI may be specified.")

        p.set_defaults(instance=self)
