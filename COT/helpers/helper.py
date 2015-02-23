#!/usr/bin/env python
#
# helper.py - Abstract provider of a non-Python helper program.
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Interface for providers of non-Python helper programs.

Provides the ability to install the program if not already present,
and the ability to run the program as well.
"""

import logging
import subprocess
from distutils.spawn import find_executable

import COT.ui_shared

logger = logging.getLogger(__name__)


class HelperNotFoundError(OSError):

    """A helper program cannot be located."""


class HelperError(EnvironmentError):

    """A helper program exited with non-zero return code."""


class Helper(object):

    """A provider of a non-Python helper program."""

    # Package managers:
    PACKAGE_MANAGERS = {
        "port":    find_executable('port'),
        "apt-get": find_executable('apt-get'),
        "yum":     find_executable('yum'),
    }

    def __init__(self, helper_name):
        self.helper = helper_name
        self.helper_path = None
        self._version = None

    @property
    def version(self):
        if self.find_helper() and not self._version:
            self._version = self._get_version()
        return self._version

    def find_helper(self):
        if not self.helper_path:
            logger.verbose("Checking for helper executable {0}"
                           .format(self.helper))
            self.helper_path = find_executable(self.helper)
        if self.helper_path:
            logger.verbose("{0} is at {1}".format(self.helper,
                                                  self.helper_path))
            return True
        else:
            logger.verbose("No path to {0} found".format(self.helper))
            return False

    def _check_call(self, args, require_success=True):
        """Wrapper for :func:`subprocess.check_call`.

        Unlike :meth:`check_output` below, this does not redirect stdout
        or stderr; all output from the subprocess will be sent to the system
        stdout/stderr as normal.

        :param list args: Command to invoke and its associated args
        :param boolean require_success: If ``False``, do not raise an error
          when the command exits with a return code other than 0

        :raise HelperNotFoundError: if the command doesn't exist
          (instead of a :class:`OSError`)

        :raise HelperError: if the command returns a value other than 0 and
          :attr:`require_success` is not ``False``
        """
        cmd = args[0]
        logger.verbose("Calling '{0}'".format(" ".join(args)))
        try:
            subprocess.check_call(args)
        except OSError as e:
            raise HelperNotFoundError(e.errno,
                                      "Unable to locate helper program '{0}'. "
                                      "Please check your $PATH.".format(cmd))
        except subprocess.CalledProcessError as e:
            if require_success:
                raise HelperError(e.returncode,
                                  "Helper program '{0}' exited with error {1}"
                                  .format(cmd, e.returncode))
        logger.debug("{0} exited successfully".format(cmd))

    def _check_output(self, args, require_success=True):
        """Wrapper for :func:`subprocess.check_output`.

        Automatically redirects stderr to stdout, captures both to a buffer,
        and generates a debug message with the stdout contents.

        :param list args: Command to invoke and its associated args
        :param boolean require_success: If ``False``, do not raise an error
          when the command exits with a return code other than 0

        :return: Captured stdout/stderr from the command
        :raise HelperNotFoundError: if the command doesn't exist
          (instead of a :class:`OSError`)

        :raise HelperError: if the command returns a value other than 0 and
          :attr:`require_success` is not ``False``
        """
        cmd = args[0]
        logger.verbose("Calling '{0}'".format(" ".join(args)))
        # In 2.7+ we can use subprocess.check_output(), but in 2.6,
        # we have to work around its absence.
        try:
            if "check_output" not in dir(subprocess):
                process = subprocess.Popen(args,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT)
                stdout, _ = process.communicate()
                retcode = process.poll()
                if retcode and require_success:
                    raise subprocess.CalledProcessError(retcode,
                                                        " ".join(args))
            else:
                stdout = (subprocess.check_output(args,
                                                  stderr=subprocess.STDOUT)
                          .decode())
        except OSError as e:
            raise HelperNotFoundError(e.errno,
                                      "Unable to locate helper program '{0}'. "
                                      "Please check your $PATH.".format(cmd))
        except subprocess.CalledProcessError as e:
            try:
                stdout = e.output.decode()
            except AttributeError:
                # CalledProcessError doesn't have 'output' in 2.6
                stdout = "(output unavailable)"
            if require_success:
                raise HelperError(e.returncode,
                                  "Helper program '{0}' exited with error {1}:"
                                  "\n> {2}\n{3}".format(cmd, e.returncode,
                                                        " ".join(args),
                                                        stdout))
        logger.verbose("{0} output:\n{1}".format(cmd, stdout))
        return stdout

    def call_helper(self, args, capture_output=True, require_success=True):
        if not self.find_helper():
            if not COT.ui_shared.CURRENT_UI.confirm(
                    "{0} does not appear to be installed.\n"
                    "Try to install it?"
                    .format(self.helper)):
                raise HelperNotFoundError(
                    1,
                    "Unable to proceed without helper program '{0}'. "
                    "Please install it and/or check your $PATH."
                    .format(self.helper))
            self.install_helper()
        args.insert(0, self.helper)
        if capture_output:
            return self._check_output(args, require_success)
        else:
            self._check_call(args, require_success)
            return None

    # Abstract interfaces to be implemented by subclasses

    def _get_version(self):
        raise NotImplementedError("not sure how to check version of {0}"
                                  .format(self.helper))

    def install_helper(self):
        if self.find_helper():
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.helper, self.helper_path))
            return
        raise NotImplementedError("Unsure how to install {0}"
                                  .format(self.helper))
