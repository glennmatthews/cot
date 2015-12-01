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

"""Module for managing VM environment configuration properties.

**Classes**

.. autosummary::
  :nosignatures:

  COTEditProperties
"""

import logging
import os.path
import textwrap

from .submodule import COTSubmodule
from .data_validation import ValueUnsupportedError, InvalidInputError

logger = logging.getLogger(__name__)


class COTEditProperties(COTSubmodule):
    """Edit OVF environment XML properties.

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`,
    :attr:`~COTSubmodule.package`,
    :attr:`~COTSubmodule.output`

    Attributes:
    :attr:`config_file`,
    :attr:`properties`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTEditProperties, self).__init__(UI)
        self._config_file = None
        self._properties = {}

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
        """List of property (key, value) tuples to update."""
        return self._properties

    @properties.setter
    def properties(self, value):
        new_value = []
        for key_value_pair in value:
            try:
                (k, v) = key_value_pair.split('=', 1)
                logger.debug("key: {0} value: {1}".format(k, v))
                if k == '':
                    raise ValueError()
                new_value.append((k, v))
            except ValueError:
                raise InvalidInputError("Invalid property '{0}' - properties "
                                        "must be in 'key=value' form"
                                        .format(key_value_pair))
        self._properties = new_value

    def run(self):
        """Do the actual work of this submodule.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTEditProperties, self).run()

        if self.config_file is not None:
            self.vm.config_file_to_properties(self.config_file)

        if self.properties:
            for key, value in self.properties:
                if value == '':
                    value = self.UI.get_input(
                        "Enter value for property '{0}'",
                        value)
                curr_value = self.vm.get_property_value(key)
                if curr_value is None:
                    self.UI.confirm_or_die(
                        "Property '{0}' does not yet exist.\n"
                        "Create it?".format(key))
                    # TODO - for new property, prompt for label/descr/type?
                self.vm.set_property_value(key, value)

        if not self.config_file and not self.properties:
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
            input = self.UI.choose_from_list(
                header="Please choose a property to edit:",
                option_list=key_list,
                info_list=string_list,
                footer=("Enter property key or number to edit, or "
                        "'q' to write changes and quit"),
                default_value='q')

            if input == 'q' or input == 'Q':
                break

            p = next(p for p in pa if p['key'] == input)

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
                    logger.info("Value for property '{0}' is unchanged"
                                .format(key))
                    break
                else:
                    try:
                        new_value = self.vm.set_property_value(key, new_value)
                        logger.info("Successfully updated property '{0}' "
                                    "value to '{1}'".format(key, new_value))
                        # Refresh!
                        pa = self.vm.environment_properties
                        break
                    except ValueUnsupportedError as e:
                        logger.error(e)
                        continue
            continue

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        :param object parent: Subparser grouping object returned by
            :meth:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
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

        storage['edit-properties'] = p
