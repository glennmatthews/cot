#!/usr/bin/env python
#
# cli.py - CLI handling for the Common OVF Tool suite
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
#
# PYTHON_ARGCOMPLETE_OK

"""CLI entry point for the Common OVF Tool (COT) suite.

**Functions**

.. autosummary::
  :nosignatures:

  formatter

**Classes**

.. autosummary::
  :nosignatures:

  CLI
"""

from __future__ import print_function

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

try:
    import argcomplete
    _argcomplete = True
except ImportError:
    _argcomplete = False

from COT import __version_long__
from COT.data_validation import InvalidInputError, ValueMismatchError
from COT.ui_shared import UI

logger = logging.getLogger(__name__)


def formatter(verbosity=logging.INFO):
    """Create formatter for log output.

    We offer different (more verbose) formatting when debugging is enabled,
    hence this need.

    Args:
      verbosity (int): Logging level as defined by :mod:`logging`.

    Returns:
      colorlog.ColoredFormatter: Formatter object to use with :mod:`logging`.
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


class CLI(UI):
    """Command-line user interface for COT.

    .. autosummary::
      :nosignatures:

      confirm
      create_parser
      create_subparsers
      fill_examples
      fill_usage
      get_input
      get_password
      main
      parse_args
      run
      set_verbosity
      terminal_width
    """

    def __init__(self, terminal_width=None):
        """Create CLI handler instance.

        Args:
          terminal_width (int): (optional) Set the terminal width for this
              CLI, independent of the actual terminal in use.
        """
        super(CLI, self).__init__(force=True)
        # In python 2.7, we want raw_input, but in python 3 we want input.
        try:
            self.input = raw_input
        except NameError:
            self.input = input
        self.getpass = getpass.getpass
        self.handler = None
        self.master_logger = None
        self._terminal_width = terminal_width
        self.wrapper = textwrap.TextWrapper(width=self.terminal_width - 1)

        if sys.hexversion >= 0x02070000:
            # not available in 2.6, oh well.
            logging.captureWarnings(True)

        self.create_parser()
        self.create_subparsers()
        if _argcomplete:
            argcomplete.autocomplete(self.parser)

        from COT.helpers import Helper
        Helper.USER_INTERFACE = self

    @property
    def terminal_width(self):
        """The width of the terminal in columns."""
        if self._terminal_width is None:
            try:
                self._terminal_width = get_terminal_size().columns
            except ValueError:
                # sometimes seen in unit tests:
                # ValueError: underlying buffer has been detached
                # Easy enough to work around...
                self._terminal_width = 80
            if self._terminal_width <= 0:
                self._terminal_width = 80
        return self._terminal_width

    def fill_usage(self, subcommand, usage_list):
        """Pretty-print a list of usage strings for a COT subcommand.

        Automatically prepends a ``cot subcommand --help`` usage string
        to the provided list.

        Args:
          subcommand (str): Subcommand name/keyword
          usage_list (list): List of usage strings for this subcommand.
        Returns:
          string: All usage strings, each appropriately wrapped to the
          :func:`terminal_width` value.

        Examples:
          ::

            >>> print(CLI(50).fill_usage('add-file',
            ...       ["FILE PACKAGE [-o OUTPUT] [-f FILE_ID]"]))
            <BLANKLINE>
              cot add-file --help
              cot <opts> add-file FILE PACKAGE [-o OUTPUT]
                                  [-f FILE_ID]
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
        width = self.terminal_width
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
        r"""Pretty-print a set of usage examples.

        Args:
          example_list (list): List of (description, CLI example) tuples.

        Returns:
          str: Concatenation of examples, each wrapped appropriately to the
          :func:`terminal_width` value. CLI examples will be wrapped with
          backslashes and a hanging indent.

        Examples:
          ::

            >>> print(CLI(68).fill_examples([
            ...  ("Deploy to vSphere/ESXi server 192.0.2.100 with credentials"
            ...   " admin/admin, creating a VM named 'test_vm' from foo.ova.",
            ...   'cot deploy foo.ova esxi 192.0.2.100 -u admin -p admin'
            ...   ' -n test_vm'),
            ...  ("Deploy to vSphere/ESXi server 192.0.2.100, with username"
            ...   " admin (prompting the user to input a password at runtime),"
            ...   " creating a VM based on profile '1CPU-2.5GB' in foo.ova.",
            ...   'cot deploy foo.ova esxi 192.0.2.100 -u admin -c 1CPU-2.5GB')
            ... ]))
            Examples:
              Deploy to vSphere/ESXi server 192.0.2.100 with credentials
              admin/admin, creating a VM named 'test_vm' from foo.ova.
            <BLANKLINE>
                cot deploy foo.ova esxi 192.0.2.100 -u admin -p admin \
                    -n test_vm
            <BLANKLINE>
              Deploy to vSphere/ESXi server 192.0.2.100, with username admin
              (prompting the user to input a password at runtime), creating a
              VM based on profile '1CPU-2.5GB' in foo.ova.
            <BLANKLINE>
                cot deploy foo.ova esxi 192.0.2.100 -u admin -c 1CPU-2.5GB
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
        width = self.terminal_width
        self.wrapper.width = width - 1
        self.wrapper.initial_indent = '  '
        self.wrapper.subsequent_indent = '  '
        self.wrapper.break_on_hyphens = False
        for (desc, example) in example_list:
            if len(output_lines) > 1:
                output_lines.append("")
            output_lines.extend(self.wrapper.wrap(desc))
            output_lines.append("")
            example_lines = example.splitlines()
            if len(example_lines) > 1:
                # Don't wrap multiline examples, just indent
                for line in example_lines:
                    output_lines.append("    "+line)
            else:
                wrapped_line = "   "
                for param in re.findall(splitter, example):
                    if len(wrapped_line) + len(param) >= (width - 4):
                        wrapped_line += " \\"
                        output_lines.append(wrapped_line)
                        wrapped_line = "       "
                    wrapped_line += " " + param
                output_lines.append(wrapped_line)
        return "\n".join(output_lines)

    def set_verbosity(self, level):
        """Enable logging and/or change the logging verbosity level.

        Will call :func:`formatter` and associate the resulting formatter
        with logging.

        Args:
          level (int): Logging level as defined by :mod:`logging`
        """
        if not self.handler:
            self.handler = logging.StreamHandler()
        self.handler.setLevel(level)
        self.handler.setFormatter(formatter(level))
        if not self.master_logger:
            self.master_logger = logging.getLogger('COT')
            self.master_logger.addHandler(self.handler)
        self.master_logger.setLevel(level)

    def run(self, argv):
        """Parse the given CLI args then run.

        Calls :func:`parse_args` followed by :func:`main`.

        Args:
          argv (list): The CLI argv value (not including argv[0])
        Returns:
          int: Return code from :func:`main`
        """
        args = self.parse_args(argv)
        return self.main(args)

    def confirm(self, prompt):
        """Prompt user to confirm the requested operation.

        Auto-accepts if :attr:`force` is set to ``True``.

        Args:
          prompt (str): Message to prompt the user with
        Returns:
          bool: ``True`` (user accepts) or ``False`` (user declines)
        """
        if self.force:
            logger.warning("Automatically agreeing to '%s'", prompt)
            return True

        # Wrap prompt to screen
        prompt_w = []
        self.wrapper.width = self.terminal_width - 1
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
        """Prompt the user to enter a string.

        Auto-inputs the :attr:`default_value` if :attr:`force` is set to
        ``True``.

        Args:
          prompt (str): Message to prompt the user with
          default_value (str): Default value to input if the user simply
              hits Enter without entering a value, or if :attr:`force`.

        Returns:
          str: Input value
        """
        if self.force:
            logger.warning("Automatically entering '%s' in response to '%s'",
                           default_value, prompt)
            return default_value

        ans = self.input("{0} [{1}] ".format(prompt, default_value))
        if ans:
            return ans
        return default_value

    def get_password(self, username, host):
        """Get password string from the user.

        Args:
          username (str): Username the password is associated with
          host (str): Host the password is associated with

        Raises:
          InvalidInputError: if :attr:`force` is ``True``
              (as there is no "default" password value)
        Returns:
          str: Password string
        """
        if self.force:
            raise InvalidInputError("No password specified for {0}@{1}"
                                    .format(username, host))
        return self.getpass("Password for {0}@{1}: "
                            .format(username, host))

    def create_parser(self):
        """Create :attr:`parser` object for global ``cot`` command.

        Includes a number of globally applicable CLI options.
        """
        # Argparse checks the environment variable COLUMNS to control
        # its line-wrapping
        os.environ['COLUMNS'] = str(self.terminal_width)
        self.wrapper.width = self.terminal_width - 1
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
            '-d', '-vv', '--debug', dest='_verbosity',
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
        """Populate the CLI sub-parsers for all known submodules.

        Creates an instance of each :class:`~COT.submodule.COTGenericSubmodule`
        subclass, then calls
        :func:`~COT.submodule.COTGenericSubmodule.create_subparser` for each.
        """
        from COT.add_disk import COTAddDisk
        from COT.add_file import COTAddFile
        from COT.deploy_esxi import COTDeployESXi
        from COT.edit_hardware import COTEditHardware
        from COT.edit_product import COTEditProduct
        from COT.edit_properties import COTEditProperties
        from COT.help import COTHelp
        from COT.info import COTInfo
        from COT.inject_config import COTInjectConfig
        from COT.install_helpers import COTInstallHelpers
        from COT.remove_file import COTRemoveFile
        for klass in [
                COTAddDisk,
                COTAddFile,
                COTDeployESXi,
                COTEditHardware,
                COTEditProduct,
                COTEditProperties,
                COTHelp,
                COTInfo,
                COTInjectConfig,
                COTInstallHelpers,
                COTRemoveFile,
        ]:
            instance = klass(self)
            # the subparser stores a reference to the instance (args.instance)
            # so we don't need to persist it here...
            instance.create_subparser()

    def add_subparser(self, title,
                      parent=None, aliases=None, lookup_prefix="",
                      **kwargs):
        """Create a subparser under the specified parent.

        Args:
          title (str): Canonical keyword for this subparser
          parent (object): Subparser grouping object returned by
              :meth:`ArgumentParser.add_subparsers`
          aliases (list): Aliases for ``title``. Only used in Python 3.x.
          lookup_prefix (str): String to prepend to ``title`` and
              each alias in ``aliases`` for lookup purposes.
          kwargs (dict): Passed through to :meth:`parent.add_parser`

        Returns:
          object: Subparser object
        """
        # Subparser aliases are only supported by argparse in Python 3.2+
        if sys.hexversion >= 0x03020000 and aliases:
            kwargs['aliases'] = aliases
        else:
            aliases = None

        if parent is None:
            parent = self.subparsers

        p = parent.add_parser(title, **kwargs)
        self.subparser_lookup[lookup_prefix + title] = p
        if aliases:
            for alias in aliases:
                self.subparser_lookup[lookup_prefix + alias] = p
        return p

    def parse_args(self, argv):
        """Parse the given CLI arguments into a namespace object.

        Args:
          argv (list): List of CLI arguments, not including argv0
        Returns:
          argparse.Namespace: Parser namespace object
        """
        # Parse the user input
        args = self.parser.parse_args(argv)

        # If being run non-interactively, treat as if --force is set, in order
        # to avoid hanging while trying to read input that will never come.
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            args._force = True  # pylint: disable=protected-access

        return args

    @staticmethod
    def args_to_dict(args):
        """Convert args to a dict and perform any needed cleanup.

        Args:
          args (argparse.Namespace): Namespace from :meth:`parse_args`.
        Returns:
          dict: Dictionary of arg to value
        """
        arg_dict = vars(args)
        del arg_dict["_verbosity"]
        del arg_dict["_force"]
        del arg_dict["_subcommand"]
        for (arg, value) in arg_dict.items():
            # When argparse is using both "nargs='+'" and "action=append",
            # this allows some flexibility in the user CLI, but the parsed
            # output is a nested list of lists. E.g., "-a 1 2 -a 3" would parse
            # as [[1, 2], [3]] rather than the desired [1, 2, 3].
            # Flatten it back out before we pass it through to the submodule!
            if (isinstance(value, list) and
                    all(isinstance(v, list) for v in value)):
                arg_dict[arg] = [v for l in value for v in l]
        return arg_dict

    @staticmethod
    def set_instance_attributes(arg_dict):
        """Set attributes of the :attr:`instance` based on the given arg_dict.

        Args:
          arg_dict (dict): Dictionary of (attribute, value).
        Raises:
          InvalidInputError: if attributes are not validly set.
        """
        # Set mandatory (CAPITALIZED) args first, then optional args
        for (arg, value) in arg_dict.items():
            if arg[0].isupper() and value is not None:
                setattr(arg_dict["instance"], arg.lower(), value)
        for (arg, value) in arg_dict.items():
            if arg == "instance":
                continue
            if not arg[0].isupper() and value is not None:
                setattr(arg_dict["instance"], arg, value)

    def main(self, args):
        """Main worker function for COT when invoked from the CLI.

        * Calls :func:`set_verbosity` with the appropriate verbosity level
          derived from the args.
        * Looks up the appropriate :class:`~COT.submodule.COTGenericSubmodule`
          instance corresponding to the subcommand that was invoked.
        * Converts :attr:`args` to a dict and calls
          :func:`~COT.submodule.COTGenericSubmodule.set_value` for each
          arg/value in the dict.
        * Calls :func:`~COT.submodule.COTGenericSubmodule.run` followed by
          :func:`~COT.submodule.COTGenericSubmodule.finished`.
        * Catches various exceptions and handles them appropriately.

        Args:
          args (argparse.Namespace): Parser namespace object returned from
              :func:`parse_args`.

        Returns:
          int: Exit code for the COT executable.

           * 0 on successful completion
           * 1 on runtime error
           * 2 on input error (parser error,
             :class:`~COT.data_validation.InvalidInputError`, etc.)
        """
        # pylint: disable=protected-access
        self.force = args._force
        self.set_verbosity(args._verbosity)

        # In python3.3+ we can get here even without a subcommand:
        if not args._subcommand:
            self.parser.error("too few arguments")

        subp = self.subparser_lookup[args._subcommand]

        # Call the appropriate submodule and handle any resulting errors
        arg_dict = self.args_to_dict(args)
        try:
            self.set_instance_attributes(arg_dict)
            args.instance.run()
            args.instance.finished()
        except (InvalidInputError, ValueMismatchError) as e:
            subp.error(e)
        except NotImplementedError as e:
            sys.exit("Missing functionality:\n{0}\n"
                     "Please contact the COT development team."
                     .format(e.args[0]))
        except EnvironmentError as e:
            # EnvironmentError may have some of (errno, strerror, filename).
            if e.errno is not None:
                if e.filename is not None:
                    # implicitly we also have e.strerror
                    print("{0}: {1}".format(e.filename, e.strerror))
                else:
                    print(e)
                sys.exit(e.errno)
            else:
                print(e.args[0])
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
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
    """Launch COT from the CLI."""
    CLI().run(sys.argv[1:])


if __name__ == "__main__":
    main()
