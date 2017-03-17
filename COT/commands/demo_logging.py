#!/usr/bin/env python
#
# March 2017, Glenn F. Matthews
# Copyright (c) 2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Provide 'demo-logging' keyword for COT CLI.

This command is not enabled in the COT CLI by default, as it is provided
primarily for development and debugging purposes.
"""
from __future__ import print_function

import logging

from .command import command_classes, Command

logger = logging.getLogger(__name__)


class COTDemoLogging(Command):
    """Provide 'demo-logging' syntax.

    Inherited attributes:
    :attr:`~Command.ui`
    """

    def run(self):
        """Display the help menu for the specified subcommand."""
        super(COTDemoLogging, self).run()

        levels = (
            (logging.ERROR, '-qq'),
            (logging.WARNING, '-q'),
            (logging.NOTICE, ''),
            (logging.INFO, '-v'),
            (logging.VERBOSE, '-vv'),
            (logging.DEBUG, '-vvv'),
            (logging.SPAM, '-vvvv'),
        )

        for (verbosity, arg) in levels:
            print('\nExample log messages at verbosity level {0}'
                  ' ("cot {1} <command>..."):'
                  .format(logging.getLevelName(verbosity), arg))
            self.ui.set_verbosity(verbosity)

            # Example "real" log messages from various COT modules:

            logger.handle(logger.makeRecord(
                logger.name, logging.ERROR,
                "ovf.py", 763,
                "Referenced file '%s' does not exist!", "critical.txt",
                None, "_refresh_file_references", None))

            logger.handle(logger.makeRecord(
                logger.name, logging.WARNING,
                "cli.py", 337,
                "Automatically agreeing to '%s'", "Format hard disk now?",
                None, "confirm", None))

            logger.handle(logger.makeRecord(
                logger.name, logging.NOTICE,
                "helper.py", 348,
                "Installing '%s'...", "qemu-img",
                None, "install", None))

            logger.handle(logger.makeRecord(
                logger.name, logging.INFO,
                "edit_properties.py", 285,
                "Value for property '%s' is unchanged", "mgmt-interface",
                None, "edit_properties_interactive", None))

            logger.handle(logger.makeRecord(
                logger.name, logging.VERBOSE,
                "deploy_esxi.py", 426,
                "Connection established", None,
                None, "fixup_serial_ports", None))

            logger.handle(logger.makeRecord(
                logger.name, logging.DEBUG,
                "inject_config.py", 285,
                "Config disk estimated size is %s, for a total of %s",
                ("78 B", "530.1 kiB"),
                None, "working_dir_disk_space_required", None))

            logger.handle(logger.makeRecord(
                logger.name, logging.SPAM,
                "xml_file.py", 187,
                "Examining %d %s elements under %s",
                (1, "VirtualSystem", "Envelope"),
                None, "find_all_children", None))

    def create_subparser(self):
        """Create 'demo-logging' CLI subparser."""
        parser = self.ui.add_subparser(
            'demo-logging',
            help="""Demonstrate COT logging output and options""",
            usage="""cot demo-logging""",
            description="Demonstrate COT logging output and options""")

        parser.set_defaults(instance=self)


command_classes.append(COTDemoLogging)
