#!/usr/bin/env python
#
# edit_properties.py - Implements "edit-properties" sub-command
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2017 the COT project developers.
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

from COT.data_validation import (
    truth_value, ValueUnsupportedError, InvalidInputError
)
from .command import command_classes, ReadWriteCommand

logger = logging.getLogger(__name__)


class COTEditProperties(ReadWriteCommand):
    """Edit OVF environment XML properties.

    Inherited attributes:
    :attr:`~Command.ui`,
    :attr:`~ReadWriteCommand.package`,
    :attr:`~ReadWriteCommand.output`

    Attributes:
    :attr:`config_file`,
    :attr:`properties`,
    :attr:`transports`,
    :attr:`user_configurable`
    """

    def __init__(self, ui):
        """Instantiate this command with the given UI.

        Args:
          ui (UI): User interface instance.
        """
        super(COTEditProperties, self).__init__(ui)
        self._config_file = None
        self._properties = []
        self.labels = []
        """List of label strings to set for the properties being updated."""
        self.descriptions = []
        """List of description strings to set for updated properties."""
        self._transports = []
        self.user_configurable = None
        """Value to set the user_configurable flag on properties we edit."""

    @property
    def config_file(self):
        """Path to plaintext file to read configuration lines from.

        Raises:
          InvalidInputError: if the file does not exist.
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
        r"""List of property (key, value, type) tuples to update.

        Properties may also be set from strings (such as by CLI)
        with the syntax ``<key>[=<value>][+<type>]``.

        Examples:
          ::

            >>> from COT.ui import UI
            >>> i = COTEditProperties(UI())
            >>> i.properties
            []
            >>> i.properties = [
            ... "no_value",
            ... "key=value",
            ... "string_type+string",
            ... "full-type=yes+boolean",
            ... ]
            >>> print("\n".join([str(p) for p in i.properties]))
            ('no_value', None, None)
            ('key', 'value', None)
            ('string_type', None, 'string')
            ('full-type', 'yes', 'boolean')
            >>> i.properties = [
            ... "ssh=autopubkey=ssh-rsa AA...q+t0...Tuw== root@MASTER",
            ... "tricky=+foo",
            ... "tricky_value=++foo==++",
            ... "trickiest=bar+foo=hello+boolean",
            ... ]
            >>> print("\n".join([str(p) for p in i.properties]))
            ('ssh', 'autopubkey=ssh-rsa AA...q+t0...Tuw== root@MASTER', None)
            ('tricky', '', 'foo')
            ('tricky_value', '++foo==++', None)
            ('trickiest', 'bar+foo=hello', 'boolean')
        """
        return self._properties

    @properties.setter
    def properties(self, value):
        new_value = []
        for prop in value:
            # While our string is delimited by '+' and '=' as "key=value+type",
            # those characters may also be included in the actual value,
            # as in an SSH private key:
            # 'autopubkey=ssh-rsa AA...gl/p...q+t0...Tuw== root@MASTER'
            # or other base64-encoded value ([A-Za-z0-9+/=] or [A-Za-z0-9-_=])
            # So we have to be "clever" in how we parse things.
            # To handle ambiguity, we presume that the characters '+' and '='
            # MAY appear in a value string but NOT in a key or prop_type.
            match = re.match(r"^([^=+]+)(=.*?)?(\+[^=+]+?)?$", prop)
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
        """Transport mechanism(s) for environment properties."""
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
        for val in value:
            if val in self._KNOWN_TRANSPORTS.keys():
                val = self._KNOWN_TRANSPORTS[val]
            if val not in self._KNOWN_TRANSPORTS.values():
                logger.warning("Unknown transport value '%s'. "
                               "You may want to contact the COT developers "
                               "to add this as a recognized value.", val)
            self._transports.append(val)

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        Returns:
          tuple: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if self.labels and not self.properties:
            return False, ("The --label option requires also specifying "
                           "a corresponding --properties option")
        if self.descriptions and not self.properties:
            return False, ("The --description option requires also specifying "
                           "a corresponding --properties option")
        if self.labels and len(self.labels) != len(self.properties):
            return False, ("The number of --label entries ({0}) and "
                           "--properties ({1}) must be equal"
                           .format(len(self.labels), len(self.properties)))
        if self.descriptions and (len(self.descriptions) !=
                                  len(self.properties)):
            return False, ("The number of --description entries ({0}) and "
                           "--properties ({1}) must be equal"
                           .format(len(self.descriptions),
                                   len(self.properties)))
        return super(COTEditProperties, self).ready_to_run()

    def run(self):
        """Do the actual work of this command.

        Raises:
          InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTEditProperties, self).run()

        if self.config_file is not None:
            self.vm.config_file_to_properties(self.config_file,
                                              self.user_configurable)

        if self.properties:
            for index in range(0, len(self.properties)):
                key, value, prop_type = self.properties[index]
                label = self.labels[index] if self.labels else None
                desc = self.descriptions[index] if self.descriptions else None
                curr_value = self.vm.get_property_value(key)
                if curr_value is None:
                    self.ui.confirm_or_die(
                        "Property '{0}' does not yet exist.\n"
                        "Create it?".format(key))
                self.vm.set_property_value(
                    key, value,
                    user_configurable=self.user_configurable,
                    property_type=prop_type,
                    label=label,
                    description=desc)

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
        proparray = self.vm.environment_properties
        while True:
            key_list = [p['key'] for p in proparray]
            string_list = ["""{0:25} "{1}" """.format(p['key'], p['label'])
                           for p in proparray]
            user_input = self.ui.choose_from_list(
                header="Please choose a property to edit:",
                option_list=key_list,
                info_list=string_list,
                footer=("Enter property key or number to edit, or "
                        "'q' to write changes and quit"),
                default_value='q')

            if user_input == 'q' or user_input == 'Q':
                break

            prop = next(p for p in proparray if p['key'] == user_input)

            key = prop['key']
            old_value = prop['value']
            prompt = "\n".join([
                wrapper.fill(format_str.format("Key:", prop['key'])),
                wrapper.fill(format_str.format("Label:", prop['label'])),
                wrapper.fill(format_str.format("Description:",
                                               prop['description'])),
                wrapper.fill(format_str.format("Type:", prop['type'])),
                wrapper.fill(format_str.format("Qualifiers:",
                                               prop['qualifiers'])),
                wrapper.fill(format_str.format("Current Value:", old_value)),
                "",
                "Enter new value for this property",
            ])

            while True:
                new_value = self.ui.get_input(prompt,
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
                        proparray = self.vm.environment_properties
                        break
                    except ValueUnsupportedError as exc:
                        logger.error(exc)
                        continue
            continue

    def create_subparser(self):
        """Create 'edit-properties' CLI subparser."""
        parser = self.ui.add_subparser(
            'edit-properties',
            aliases=['set-properties', 'edit-environment', 'set-environment'],
            add_help=False,
            help="""Edit or create environment properties of an OVF""",
            usage=self.ui.fill_usage("edit-properties", [
                "PACKAGE [-p KEY1=VALUE1 [-p KEY2=VALUE2 ...]] "
                "[-l LABEL1 [-l LABEL2 ...]] [-d DESC1 [-d DESC2 ...]] "
                "[-c CONFIG_FILE] [-u [USER_CONFIGURABLE]] "
                "[-t TRANSPORT [TRANSPORT2 ...]] [-o OUTPUT]",
                "PACKAGE [-u [USER_CONFIGURABLE]] [-o OUTPUT]",
            ]),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
Configure environment properties of the given OVF or OVA. The user may specify
keys and values as command-line arguments or may provide a config-file to
read from. If neither --config-file, --properties, nor --transport are given,
the program will run interactively.""",
            epilog=self.ui.fill_examples([
                ("Add configuration from a text file and mark the resulting"
                 " properties as non-user-configurable.",
                 'cot edit-properties input.ovf -c config.txt -u=0'),
                ("Add/update two properties, one a string with no default"
                 " value and the other a boolean defaulting to true, and"
                 " mark both properties as user-configurable.",
                 'cot edit-properties input.ovf -p string-property+string'
                 ' -p bool-property=true+boolean --user-configurable'),
                ("Update the label and description of two existing properties",
                 'cot edit-properties input.ovf -p hostname -l "Hostname"'
                 ' -d "Hostname of this device" -p enable-ssh -l "Enable'
                 ' remote SSH access" -d "Enable sshd and disable telnetd"'),
            ]),
        )

        parser.add_argument('PACKAGE',
                            help="""OVF descriptor or OVA file to edit""")

        group = parser.add_argument_group("general options")

        group.add_argument('-h', '--help', action='help',
                           help="""Show this help message and exit""")
        group.add_argument('-o', '--output',
                           help="Name/path of new OVF/OVA package to create "
                           "instead of updating the existing OVF")

        group = parser.add_argument_group("property setting options")

        group.add_argument('-u', '--user-configurable',
                           nargs='?', const="true", type=truth_value,
                           help="Update the 'userConfigurable' flag on all "
                           "edited properties to True or the given value")

        group.add_argument(
            '-c', '--config-file',
            help="Read configuration CLI from this text file and generate"
            " generic properties for each line of CLI")
        group.add_argument(
            '-p', '--properties', action='append', nargs='+',
            metavar=('KEY1[=VALUE1][+TYPE1]', 'K2[=V2][+T2]'),
            help="Update or create the given property keys. "
            "A '=' delimits the optional value to set this key to. "
            "A '+' delimits the optional type to enforce for this key. "
            "This argument may be repeated as needed to specify multiple"
            " properties to edit.")
        group.add_argument(
            '-l', '--labels', action='append', nargs='+',
            metavar=('LABEL1', 'LABEL2'),
            help="Set the label(s) for the property(s) being edited. "
            "If this option is specified, the number of properties and"
            " the number of labels *must* be equal.")
        group.add_argument(
            '-d', '--descriptions', action='append', nargs='+',
            metavar=('DESC1', 'DESC2'),
            help="Set the description(s) for the property(s) being edited. "
            "If this option is specified, the number of properties and the"
            " number of descriptions *must* be equal.")
        group.add_argument(
            '-t', '--transports', action='append', nargs='+',
            metavar=('TRANSPORT', 'TRANSPORT2'),
            help="Set the transport method(s) for properties. "
            "Known values are 'iso', 'vmware', and 'ibm',"
            " or an arbitrary URI may be specified.")

        parser.set_defaults(instance=self)


command_classes.append(COTEditProperties)


if __name__ == "__main__":   # pragma: no cover
    import doctest
    doctest.testmod()
