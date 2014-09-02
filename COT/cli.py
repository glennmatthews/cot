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

from COT import __version__, __version_long__

# In python 2.7, we want raw_input, but in python 3 we want input.
try: input = raw_input
except NameError: pass

def mac_address(string):
    """Parser helper function - validate string is a valid MAC address"""
    if not re.match("([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", string):
        msg = "'{0}' is not a valid MAC address".format(string)
        raise argparse.ArgumentTypeError(msg)
    return string


def device_address(string):
    """Parser helper function - validate string is an appropriately formed
    device address such as '1:0'
    """
    if not re.match("\d+:\d+$", string):
        msg = "'{0}' is not a valid device address".format(string)
        raise argparse.ArgumentTypeError(msg)
    return string


def no_whitespace(string):
    """Parser helper function - for arguments not allowed to contain
    any whitespace"""
    if len(string.split()) > 1:
        msg = ("'{0}' contains invalid whitespace".format(string))
        raise argparse.ArgumentTypeError(msg)
    return string


def non_negative_int(string):
    """Parser helper function - for numerical arguments that must be 0 or more.
    """
    try:
        i = int(string)
        if i < 0:
            raise argparse.ArgumentTypeError("value must be at least 0"
                                             .format(string))
    except ValueError:
        raise argparse.ArgumentTypeError("expected non-negative number but "
                                         "got '{0}'".format(string))
    return i


def positive_int(string):
    """Parser helper function - for numerical arguments that must be 1 or more.
    """
    try:
        i = int(string)
        if i <= 0:
            raise argparse.ArgumentTypeError("value must be at least 1"
                                             .format(string))
    except ValueError:
        raise argparse.ArgumentTypeError("expected positive integer but "
                                         "got '{0}'".format(string))
    return i


def confirm(prompt, force=False):
    """Prompts user to confirm the requested operation, or auto-accepts if
       args.force is set to True."""
    if force:
        logger = logging.getLogger('cot')
        logger.warning("Automatically agreeing to '{0}'".format(prompt))
        return True

    while True:
        ans = input("{0} [y] ".format(prompt))
        if not ans or ans == 'y' or ans == 'Y':
            return True
        elif ans == 'n' or ans == 'N':
            return False
        else:
            print("Please enter 'y' or 'n'")


def confirm_or_die(prompt, force=False):
    """If the user doesn't agree, abort!"""
    if not confirm(prompt, force):
        sys.exit("Aborting.")


def get_input(prompt, default, force=False):
    """Prompt the user to enter a string, or auto-accepts the default if
    force is set to True."""
    if force:
        logger = logging.getLogger('cot')
        logger.warning("Automatically entering {0} in response to '{1}'"
                       .format(default, prompt))
        return default

    ans = input("{0} [{1}] ".format(prompt, default))
    if ans:
        return ans
    return default


# Top-level command definition and any global options
parser = argparse.ArgumentParser(
    #If we set "usage" here, it apparently overrides the value of "prog"
    #as well, which results in subparser help being ugly in a number of ways.
    #Hence we leave usage to the default here then manually set it in main()
    #once all of the subparsers have been initialized with the correct prog.
    #usage=("\n  %(prog)s --help"
    #       "\n  %(prog)s --version"
    #       "\n  %(prog)s <command> --help"
    #       "\n  %(prog)s [-f] [-v] <command> <options>"),
    description=(__version_long__ + """
A tool for editing Open Virtualization Format (.ovf, .ova) virtual appliances,
with a focus on virtualized network appliances such as the Cisco CSR 1000V and
Cisco IOS XRv platforms."""),
    epilog=(
"""Note: some subcommands rely on external software tools, including:
* vmdktool (http://www.freshports.org/sysutils/vmdktool/)
* qemu-img (http://www.qemu.org/)
* mkisofs  (http://cdrecord.org/
* fatdisk  (http://github.com/goblinhack/fatdisk)
* ovftool  (https://www.vmware.com/support/developer/ovf/)
"""),
    formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument('-V', '--version', action='version',
                    version=__version_long__)
parser.add_argument('-f', '--force',  action='store_true',
                    help="""Perform requested actions without prompting
                            for confirmation""")

debug_group = parser.add_mutually_exclusive_group()
#debug_group.add_argument('-q', '--quiet', action='store_true',
#                         help="""Suppress normal program output""")
debug_group.add_argument('-v', '--verbose', action='count', default=0,
                         help="""Increase verbosity of the program
                                 (repeatable)""")


# Subcommand definitions
subparsers = parser.add_subparsers(dest='subcommand', metavar="<command>",
                                   title="commands")

subparser_lookup = {}

def main():
    # Add supported subcommands to main parser
    import COT.add_disk
    import COT.add_file
    import COT.deploy
    import COT.edit_hardware
    import COT.edit_product
    import COT.edit_properties
    import COT.info
    import COT.inject_config

    # By now all subparsers have been created so we can safely set usage.
    # See comment above.
    parser.usage=("\n  %(prog)s --help"
                  "\n  %(prog)s --version"
                  "\n  %(prog)s <command> --help"
                  "\n  %(prog)s [-f] [-v] <command> <options>"
                  .format(prog=os.path.basename(sys.argv[0])))

    # Parse the user input
    args = parser.parse_args()

    # If being run non-interactively, treat as if --force is set, in order
    # to avoid hanging while trying to read input that will never come.
    if not sys.__stdin__.isatty():
        args.force = True

    logging.basicConfig()
    logger = logging.getLogger('cot')
    # Map verbosity to logging level
    log_level = {0: logging.ERROR,
                 1: logging.WARNING,
                 2: logging.INFO}
    # Any verbosity in excess of 2 gets mapped to logging.DEBUG
    logger.setLevel(log_level.get(args.verbose, logging.DEBUG))

    if not args.subcommand:
        parser.error("too few arguments")

    subp = subparser_lookup[args.subcommand]

    # General input sanity:
    if hasattr(args, "PACKAGE") and not os.path.exists(args.PACKAGE):
        subp.error("Specified package {0} does not exist!"
                   .format(args.PACKAGE))
    if hasattr(args, "PACKAGE_LIST"):
        for package in args.PACKAGE_LIST:
            if not os.path.exists(package):
                subp.error("Specified package {0} does not exist!"
                           .format(package))

    # Do any general-purpose input validation:
    if hasattr(args, "output"):
        if args.output is None:
            args.output = args.PACKAGE
        if os.path.exists(args.output):
            confirm_or_die("Overwrite existing file {0}?".format(args.output),
                           args.force)

    # Call the appropriate subcommand function and handle any resulting errors
    try:
        args.func(args)
    except NotImplementedError as e:
        sys.exit("Missing functionality:\n{0}\n"
                 "Please contact the COT development team."
                 .format(e.args[0]))
    except EnvironmentError as e:
        print(e.strerror)
        sys.exit(e.errno)
    # All exceptions not handled explicitly above will result in a
    # stack trace and exit - this is ugly so the more specific handling we
    # can provide, the better!
    return 0
