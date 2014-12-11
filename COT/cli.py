#!/usr/bin/env python
#
# cli.py - CLI handling for the Common OVF Tool suite
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

import sys
import argparse
import logging
import os.path
import re
import textwrap

from COT import __version__, __version_long__
from .data_validation import InvalidInputError
from .data_validation import *
from .ui_shared import UI

logger = logging.getLogger(__name__)

# Where do we want to wrap lines when pretty-printing?
TEXT_WIDTH = 79

class CLI(UI):
    """Command-line user interface for COT"""

    # In python 2.7, we want raw_input, but in python 3 we want input.
    try: input = raw_input
    except NameError: pass

    def __init__(self):
        self.create_parser()
        self.create_subparsers()
        args = self.parse_args()
        super(CLI, self).__init__(args.force)
        self.main(args)


    def confirm(self, prompt):
        """Prompts user to confirm the requested operation, or auto-accepts if
        args.force is set to True."""
        if self.force:
            logger.warning("Automatically agreeing to '{0}'".format(prompt))
            return True

        # Wrap prompt to screen
        prompt_w = []
        for line in prompt.splitlines():
            prompt_w.append(textwrap.fill(line, TEXT_WIDTH,
                                          break_on_hyphens=False))
        prompt = "\n".join(prompt_w)

        while True:
            ans = input("{0} [y] ".format(prompt))
            if not ans or ans == 'y' or ans == 'Y':
                return True
            elif ans == 'n' or ans == 'N':
                return False
            else:
                print("Please enter 'y' or 'n'")


    def get_input(self, prompt, default_value):
        """Prompt the user to enter a string, or auto-accepts the default if
        force is set to True."""
        if self.force:
            logger.warning("Automatically entering {0} in response to '{1}'"
                           .format(default_value, prompt))
            return default_value

        ans = input("{0} [{1}] ".format(prompt, default_value))
        if ans:
            return ans
        return default_value

    def get_password(self, username, host):
        """Get password string from the user."""
        if self.force:
            raise InvalidInputError("No password specified for {0}@{1}"
                                    .format(username, host))
        import getpass
        return getpass.getpass("Password for {0}@{1}: "
                               .format(username, host))

    def create_parser(self):
        # Top-level command definition and any global options
        parser = argparse.ArgumentParser(
            # If we set "usage" here, it apparently overrides the value of
            # "prog" as well, which results in subparser help being ugly in
            # a number of ways. Hence we leave usage to the default here then
            # manually set it in parse_args() once all of the subparsers
            # have been initialized with the correct prog.
            # usage=("\n  %(prog)s --help"
            #        "\n  %(prog)s --version"
            #        "\n  %(prog)s <command> --help"
            #        "\n  %(prog)s [-f] [-v] <command> <options>"),
            description=(__version_long__ + """
A tool for editing Open Virtualization Format (.ovf, .ova) virtual appliances,
with a focus on virtualized network appliances such as the Cisco CSR 1000V and
Cisco IOS XRv platforms."""),
            epilog=(
"""Note: some subcommands rely on external software tools, including:
* qemu-img (http://www.qemu.org/)
* mkisofs  (http://cdrecord.org/)
* ovftool  (https://www.vmware.com/support/developer/ovf/)
* fatdisk  (http://github.com/goblinhack/fatdisk)
* vmdktool (http://www.freshports.org/sysutils/vmdktool/)
"""),
            formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument('-V', '--version', action='version',
                            version=__version_long__)
        parser.add_argument('-f', '--force',  action='store_true',
                            help="""Perform requested actions without """
                            """prompting for confirmation""")

        debug_group = parser.add_mutually_exclusive_group()
        #debug_group.add_argument('-q', '--quiet', action='store_true',
        #                         help="""Suppress normal program output""")
        debug_group.add_argument('-v', '--verbose', action='count', default=0,
                                 help="""Increase verbosity of the program """
                                 """(repeatable)""")

        self.parser = parser

        # Subcommand definitions
        self.subparsers = parser.add_subparsers(dest='subcommand',
                                                metavar="<command>",
                                                title="commands")

        self.subparser_lookup = {}


    def create_subparsers(self):
        import COT.add_disk
        import COT.add_file
        import COT.deploy
        import COT.edit_hardware
        import COT.edit_product
        import COT.edit_properties
        import COT.info
        import COT.inject_config

        # Add supported subcommands to main parser
        for module in [COT.add_disk, COT.add_file, COT.deploy,
                       COT.edit_hardware, COT.edit_product,
                       COT.edit_properties, COT.info,
                       COT.inject_config]:
            name, subparser = module.create_subparser(self.subparsers)
            self.subparser_lookup[name] = subparser


    def parse_args(self):
        # By now all subparsers have been created so we can safely set usage.
        # See comment above.
        self.parser.usage=("\n  %(prog)s --help"
                           "\n  %(prog)s --version"
                           "\n  %(prog)s <command> --help"
                           "\n  %(prog)s [-f] [-v] <command> <options>"
                           .format(prog=os.path.basename(sys.argv[0])))
        # Parse the user input
        args = self.parser.parse_args()

        # If being run non-interactively, treat as if --force is set, in order
        # to avoid hanging while trying to read input that will never come.
        if not sys.__stdin__.isatty():
            args.force = True

        return args


    def main(self, args):
        logger = logging.getLogger('COT')
        # Map verbosity to logging level
        log_level = {0: logging.ERROR,
                     1: logging.WARNING,
                     2: logging.INFO}
        # Any verbosity in excess of 2 gets mapped to logging.DEBUG
        logger.setLevel(log_level.get(args.verbose, logging.DEBUG))

        if not args.subcommand:
            self.parser.error("too few arguments")

        subp = self.subparser_lookup[args.subcommand]

        # General input sanity:
        if hasattr(args, "PACKAGE") and not os.path.exists(args.PACKAGE):
            subp.error("Specified package {0} does not exist!"
                       .format(args.PACKAGE))
        if hasattr(args, "PACKAGE_LIST"):
            for package in args.PACKAGE_LIST:
                if not os.path.exists(package):
                    subp.error("Specified package {0} does not exist!"
                               .format(package))

        try:
            if hasattr(args, "output"):
                if args.output is None:
                    args.output = args.PACKAGE
                if os.path.exists(args.output):
                    self.confirm_or_die("Overwrite existing file {0}?"
                                        .format(args.output))

            # Call the appropriate subcommand func and handle any errors
            args.func(UI=self, **vars(args))
        except InvalidInputError as e:
            subp.error(e)
        except NotImplementedError as e:
            sys.exit("Missing functionality:\n{0}\n"
                     "Please contact the COT development team."
                     .format(e.args[0]))
        except EnvironmentError as e:
            print(e.strerror)
            sys.exit(e.errno)
        except KeyboardInterrupt:
            sys.exit("\nAborted by user.")
        # All exceptions not handled explicitly above will result in a
        # stack trace and exit - this is ugly so the more specific handling we
        # can provide, the better!
        return 0

def main():
    CLI()
