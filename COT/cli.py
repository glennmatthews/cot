#!/usr/bin/env python
#
# cli.py - CLI handling for the Common OVF Tool suite
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

import os
import sys
import argparse
import re
import logging
import getpass
import textwrap

# get_terminal_size() is part of the standard library in python 3.3 and later
try:
    from shutil import get_terminal_size
except ImportError:
    from backports.shutil_get_terminal_size import get_terminal_size

from COT import __version_long__
from COT.data_validation import InvalidInputError
from COT.ui_shared import UI

logger = logging.getLogger(__name__)


class CLI(UI):
    """Command-line user interface for COT"""

    def __init__(self):
        super(CLI, self).__init__(force=True)
        # In python 2.7, we want raw_input, but in python 3 we want input.
        try:
            self.input = raw_input
        except NameError:
            self.input = input
        self.getpass = getpass.getpass
        self.handler = None
        self.master_logger = None
        self.wrapper = textwrap.TextWrapper(width=self.terminal_width() - 1)

        self.create_parser()
        self.create_subparsers()

    def terminal_width(self):
        """Returns the width of the terminal in columns."""
        return get_terminal_size().columns

    def fill_usage(self, subcommand, usage_list):
        """Pretty-print a list of usage strings for a COT subcommand.
        Automatically prepends a --help usage string.
        """
        # Automatically add a line for --help to the usage
        output_lines = ["\n  cot "+subcommand+" --help"]
        # Prefix for all other usage lines:
        prefix = "  cot <opts> {0}".format(subcommand)
        # We don't want to use standard 'textwrap' because we'd like to keep
        # usage groups together, while textwrap only pays attention to
        # whitespace, so textwrap might wrap a line as follows:
        # cot subcommand PACKAGE [-o
        #                OUTPUT]
        # ...but we instead want to wrap the whole command group, as:
        # cot subcommand PACKAGE
        #                [-o OUTPUT]
        splitter = re.compile(r"""
          \(.*?\)+   |  # Params inside (possibly nested) parens
          \[.*?\]+   |  # Params inside (possibly nested) brackets
          -\S+\s+\S+ |  # Dashed arg followed by metavar
          \S+           # Positional arg
        """, re.VERBOSE)
        width = self.terminal_width()
        for line in usage_list:
            usage_groups = re.findall(splitter, line)

            # Our preferred wrapping is like this:
            #   cot <opts> subcommand1 FOO BAR [-b BAZ]
            #                          [-t BAT] [-q | -v]
            #   cot <opts> subcommand2 BAR [-b BAZ]
            #                          [-t BAT] [-q | -v]
            # (aligning wrapped params at the end of 'subcommand')
            # but if the terminal is relatively narrow or the
            # subcommand or params are very long, we can
            # wrap with shorter indentation to the end of 'cot':
            #   cot <opts> really-long-subcommand FOO
            #       BAR [-b BAZ] [-t BAT] [-q | -v]
            #   cot <opts> subcommand BAR [-b BAZ]
            #       [-v VERBOSE_PARAM_NAME] [-t BAT]
            max_group_len = max([len(s) for s in usage_groups])
            if len(prefix) + max_group_len >= width:
                indent_line = "     "
            else:
                indent_line = " "*len(prefix)

            wrapped_line = prefix
            for group in usage_groups:
                if len(wrapped_line) + len(group) >= width:
                    # time to save this line and start a new one
                    output_lines.append(wrapped_line)
                    wrapped_line = indent_line
                wrapped_line += " " + group
            output_lines.append(wrapped_line)
        return "\n".join(output_lines)

    def fill_examples(self, example_list):
        """Pretty-print a set of usage examples.
        example_list == [(example1, desc1), (example2, desc2), ...]
        """
        output_lines = ["Examples:"]
        # Just as in fill_usage, the default textwrap behavior
        # results in less-than-ideal formatting for CLI examples.
        # So we'll do it ourselves:
        splitter = re.compile(r"""
          -\S+[ =]\S+   |  # Dashed arg followed by simple value
          -\S+[ =]".*?" |  # Dashed arg followed by quoted value
          \S+              # Positional arg
        """, re.VERBOSE)
        width = self.terminal_width()
        self.wrapper.width = width - 1
        self.wrapper.initial_indent = '    '
        self.wrapper.subsequent_indent = '    '
        self.wrapper.break_on_hyphens = False
        for (example, desc) in example_list:
            if len(output_lines) > 1:
                output_lines.append("")
            wrapped_line = " "
            for param in re.findall(splitter, example):
                if len(wrapped_line) + len(param) >= (width - 2):
                    wrapped_line += " \\"
                    output_lines.append(wrapped_line)
                    wrapped_line = "       "
                wrapped_line += " " + param
            output_lines.append(wrapped_line)
            output_lines.extend(self.wrapper.wrap(desc))
        return "\n".join(output_lines)

    def formatter(self, verbosity=logging.INFO):
        """Create formatter for log output.
        We offer different (more verbose) formatting when debugging is enabled,
        hence this need.
        """
        from colorlog import ColoredFormatter
        log_colors = {
            'DEBUG':    'blue',
            'VERBOSE':  'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red',
        }
        format_string = "%(log_color)s"
        datefmt = None
        if verbosity <= logging.DEBUG:
            format_string += "%(asctime)s.%(msecs)d "
            datefmt = "%H:%M:%S"
        format_string += "%(levelname)8s: "
        if verbosity <= logging.VERBOSE:
            format_string += "%(name)-22s "
        format_string += "%(message)s"
        return ColoredFormatter(format_string,
                                datefmt=datefmt,
                                log_colors=log_colors)

    def set_verbosity(self, level):
        if not self.handler:
            self.handler = logging.StreamHandler()
        self.handler.setLevel(level)
        self.handler.setFormatter(self.formatter(level))
        if not self.master_logger:
            self.master_logger = logging.getLogger('COT')
            self.master_logger.addHandler(self.handler)
        self.master_logger.setLevel(level)

    def run(self, argv):
        args = self.parse_args(argv)
        return self.main(args)

    def confirm(self, prompt):
        """Prompts user to confirm the requested operation, or auto-accepts if
        force is set to True."""
        if self.force:
            logger.warning("Automatically agreeing to '{0}'".format(prompt))
            return True

        # Wrap prompt to screen
        prompt_w = []
        self.wrapper.width = self.terminal_width() - 1
        self.wrapper.initial_indent = ''
        self.wrapper.subsequent_indent = ''
        self.wrapper.break_on_hyphens = False
        for line in prompt.splitlines():
            prompt_w.extend(self.wrapper.wrap(line))
        prompt = "\n".join(prompt_w)

        while True:
            ans = self.input("{0} [y] ".format(prompt))
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
            logger.warning("Automatically entering '{0}' in response to '{1}'"
                           .format(default_value, prompt))
            return default_value

        ans = self.input("{0} [{1}] ".format(prompt, default_value))
        if ans:
            return ans
        return default_value

    def get_password(self, username, host):
        """Get password string from the user."""
        if self.force:
            raise InvalidInputError("No password specified for {0}@{1}"
                                    .format(username, host))
        return self.getpass("Password for {0}@{1}: "
                            .format(username, host))

    def create_parser(self):
        # Top-level command definition and any global options

        # Argparse checks the environment variable COLUMNS to control
        # its line-wrapping
        os.environ['COLUMNS'] = str(self.terminal_width())
        self.wrapper.width = self.terminal_width() - 1
        self.wrapper.initial_indent = ''
        self.wrapper.subsequent_indent = ''
        parser = argparse.ArgumentParser(
            prog="cot",
            usage="""
  cot --help
  cot --version
  cot help <command>
  cot <command> --help
  cot <options> <command> <command-options>""",
            description=(__version_long__ + "\n" + self.wrapper.fill(
                "A tool for editing Open Virtualization Format (.ovf, .ova) "
                "virtual appliances, with a focus on virtualized network "
                "appliances such as the Cisco CSR 1000V and Cisco IOS XRv "
                "platforms.")),
            epilog=("""
Note: some subcommands rely on external software tools, including:
* qemu-img (http://www.qemu.org/)
* mkisofs  (http://cdrecord.org/)
* ovftool  (https://www.vmware.com/support/developer/ovf/)
* fatdisk  (http://github.com/goblinhack/fatdisk)
* vmdktool (http://www.freshports.org/sysutils/vmdktool/)
"""),
            formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument('-V', '--version', action='version',
                            version=__version_long__)
        parser.add_argument('-f', '--force', dest='_force',
                            action='store_true',
                            help="""Perform requested actions without """
                            """prompting for confirmation""")

        parser.set_defaults(_verbosity=logging.INFO)
        debug_group = parser.add_mutually_exclusive_group()
        debug_group.add_argument(
            '-q', '--quiet', dest='_verbosity',
            action='store_const', const=logging.WARNING,
            help="Quiet output and logging (warnings and errors only)")
        debug_group.add_argument(
            '-v', '--verbose', dest='_verbosity',
            action='store_const', const=logging.VERBOSE,
            help="Verbose output and logging")
        debug_group.add_argument(
            '-vv', '-d', '--debug', dest='_verbosity',
            action='store_const', const=logging.DEBUG,
            help="Debug (most verbose) output and logging")

        self.parser = parser

        # Subcommand definitions
        self.subparsers = parser.add_subparsers(prog="cot",
                                                dest='_subcommand',
                                                metavar="<command>",
                                                title="commands")

        self.subparser_lookup = {}

    def create_subparsers(self):
        from COT.add_disk import COTAddDisk
        from COT.add_file import COTAddFile
        from COT.deploy import COTDeployESXi
        from COT.edit_hardware import COTEditHardware
        from COT.edit_product import COTEditProduct
        from COT.edit_properties import COTEditProperties
        from COT.help import COTHelp
        from COT.info import COTInfo
        from COT.inject_config import COTInjectConfig
        for klass in [
                COTAddDisk,
                COTAddFile,
                COTDeployESXi,
                COTEditHardware,
                COTEditProduct,
                COTEditProperties,
                COTInfo,
                COTInjectConfig,
                COTHelp,   # last so it can be aware of all of the above
        ]:
            name, subparser = klass(self).create_subparser(self.subparsers)
            self.subparser_lookup[name] = subparser

    def parse_args(self, argv):
        # Parse the user input
        args = self.parser.parse_args(argv)

        # If being run non-interactively, treat as if --force is set, in order
        # to avoid hanging while trying to read input that will never come.
        if not sys.stdin.isatty():
            args._force = True

        return args

    def main(self, args):
        self.force = args._force
        self.set_verbosity(args._verbosity)

        # In python3.3+ we can get here even without a subcommand:
        if not args._subcommand:
            self.parser.error("too few arguments")

        subp = self.subparser_lookup[args._subcommand]

        # Call the appropriate submodule and handle any resulting errors
        arg_hash = vars(args)
        del arg_hash["_verbosity"]
        del arg_hash["_force"]
        del arg_hash["_subcommand"]
        for (arg, value) in arg_hash.items():
            # When argparse is using both "nargs='+'" and "action=append",
            # this allows some flexibility in the user CLI, but the parsed
            # output is a nested list of lists. E.g., "-a 1 2 -a 3" would parse
            # as [[1, 2][3]] rather than the desired [1, 2, 3].
            # Flatten it back out before we pass it through to the submodule!
            if (isinstance(value, list) and
                    all(isinstance(v, list) for v in value)):
                arg_hash[arg] = [v for l in value for v in l]
        try:
            # Set mandatory (CAPITALIZED) args first, then optional args
            for (arg, value) in arg_hash.items():
                if arg[0].isupper() and value is not None:
                    setattr(args.instance, arg.lower(), value)
            for (arg, value) in arg_hash.items():
                if arg == "instance":
                    continue
                if not arg[0].isupper() and value is not None:
                    setattr(args.instance, arg, value)
            args.instance.run()
            args.instance.finished()
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
        finally:
            if self.master_logger:
                self.master_logger.removeHandler(self.handler)
                self.master_logger = None
                self.handler.close()
                self.handler = None
            args.instance.destroy()
        # All exceptions not handled explicitly above will result in a
        # stack trace and exit - this is ugly so the more specific handling we
        # can provide, the better!
        return 0


def main():
    CLI().run(sys.argv[1:])

if __name__ == "__main__":
    main()
