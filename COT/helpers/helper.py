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

import contextlib
import logging
import os.path
import re
import subprocess
import tarfile
from distutils.spawn import find_executable
from distutils.version import StrictVersion

try:
    # Python 3.x
    from tempfile import TemporaryDirectory
except ImportError:
    # Python 2.x
    import shutil
    import tempfile

    @contextlib.contextmanager
    def TemporaryDirectory(suffix='', prefix='tmp', dir=None):
        """Create a temporary directory and make sure it's deleted later."""
        tempdir = tempfile.mkdtemp(suffix, prefix, dir)
        try:
            yield tempdir
        finally:
            shutil.rmtree(tempdir)

try:
    # Python 3.x
    from urllib.request import urlretrieve
except ImportError:
    # Python 2.x
    from urllib import urlretrieve

from verboselogs import VerboseLogger
logging.setLoggerClass(VerboseLogger)
logger = logging.getLogger(__name__)


# Default method to be used when COT.helpers is run by itself without
# the broader COT package.
# The COT package will override this with e.g. the CLI.confirm method.
def confirm(prompt, force=False):
    """Prompt user to confirm the requested operation.

    Auto-accepts if :attr:`force` is set to ``True``.

    :param str prompt: Message to prompt the user with
    :return: ``True`` (user confirms acceptance) or ``False``
      (user declines)
    """
    return True


class HelperNotFoundError(OSError):

    """A helper program cannot be located."""


class HelperError(EnvironmentError):

    """A helper program exited with non-zero return code."""


class Helper(object):

    """A provider of a non-Python helper program.

    **Properties**

    .. autosummary::
      :nosignatures:

      PACKAGE_MANAGERS
      version

    **Methods**

    .. autosummary::
      :nosignatures:

      find_executable
      find_helper
      call_helper
      download_and_expand
      apt_install
      port_install
      yum_install
      install_helper
    """

    PACKAGE_MANAGERS = {
        "port":    find_executable('port'),
        "apt-get": find_executable('apt-get'),
        "yum":     find_executable('yum'),
    }
    """Class-level lookup for package manager executables."""

    def __init__(self, helper_name, version_args=None,
                 version_regexp="([0-9.]+"):
        """Initializer.

        :param helper_name: Name of helper executable
        :param list version_args: Args to pass to the helper to
          get its version. Defaults to ``['--version']`` if unset.
        :param version_regexp: Regexp to get the version number from
          the output of the command.
        """
        self.helper = helper_name
        """Name of this helper executable"""
        self.helper_path = None
        """Discovered path to the helper on this system"""
        self.find_executable = find_executable
        self._version = None
        if not version_args:
            version_args = ['--version']
        self._version_args = version_args
        self._version_regexp = version_regexp

    @property
    def version(self):
        """Release version of the associated helper program.

        :raise: :exc:`NotImplementedError` as this must be implemented
          by a concrete subclass.
        """
        if self.find_helper() and not self._version:
            output = self.call_helper(self._version_args,
                                      require_success=False)
            match = re.search(self._version_regexp, output)
            if not match:
                raise RuntimeError("Unable to find version number in output!")
            self._version = StrictVersion(match.group(1))
        return self._version

    def find_helper(self):
        """Locate the helper program and cache its path.

        :return: ``True`` if helper has been found, else ``False``.
        """
        if not self.helper_path:
            logger.verbose("Checking for helper executable {0}"
                           .format(self.helper))
            self.helper_path = self.find_executable(self.helper)
        if self.helper_path:
            logger.verbose("{0} is at {1}".format(self.helper,
                                                  self.helper_path))
            return True
        else:
            logger.verbose("No path to {0} found".format(self.helper))
            return False

    def _check_call(self, args, require_success=True, **kwargs):
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
        logger.info("Calling '{0}'...".format(" ".join(args)))
        try:
            subprocess.check_call(args, **kwargs)
        except OSError as e:
            raise HelperNotFoundError(e.errno,
                                      "Unable to locate helper program '{0}'. "
                                      "Please check your $PATH.".format(cmd))
        except subprocess.CalledProcessError as e:
            if require_success:
                raise HelperError(e.returncode,
                                  "Helper program '{0}' exited with error {1}"
                                  .format(cmd, e.returncode))
        logger.info("...done")
        logger.debug("{0} exited successfully".format(cmd))

    def _check_output(self, args, require_success=True, **kwargs):
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
        logger.info("Calling '{0}' and capturing its output..."
                    .format(" ".join(args)))
        # In 2.7+ we can use subprocess.check_output(), but in 2.6,
        # we have to work around its absence.
        try:
            if "check_output" not in dir(subprocess):
                process = subprocess.Popen(args,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT,
                                           **kwargs)
                stdout, _ = process.communicate()
                retcode = process.poll()
                if retcode and require_success:
                    raise subprocess.CalledProcessError(retcode,
                                                        " ".join(args))
            else:
                stdout = (subprocess.check_output(args,
                                                  stderr=subprocess.STDOUT,
                                                  **kwargs)
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
        logger.info("...done")
        logger.verbose("{0} output:\n{1}".format(cmd, stdout))
        return stdout

    def call_helper(self, args, capture_output=True, require_success=True):
        """Call the helper program with the given arguments.

        :param list args: List of arguments to the helper program.
        :param boolean capture_output: If ``True``, stdout/stderr will be
          redirected to a buffer and returned, instead of being displayed
          to the user.
        :param boolean require_success: if ``True``, an exception will be
          raised if the helper exits with a non-zero status code.
        :return: Captured stdout/stderr (if :attr:`capture_output`),
          else ``None``.
        """
        if not self.find_helper():
            if not confirm("{0} does not appear to be installed.\n"
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

    @contextlib.contextmanager
    def download_and_expand(self, url):
        """Context manager for downloading and expanding a .tar.gz file.

        Creates a temporary directory, downloads the specified URL into
        the directory, unzips and untars the file into this directory,
        then yields to the given block. When the block exits, the temporary
        directory and its contents are deleted.

        ::

          with self.download_and_expand("http://example.com/foo.tgz") as d:
            # archive contents have been extracted to 'd'
            ...
          # d is automatically cleaned up.

        :param str url: URL of a .tgz or .tar.gz file to download.
        """
        with TemporaryDirectory(prefix=("cot_" + self.helper)) as d:
            logger.debug("Temporary directory is {0}".format(d))
            logger.verbose("Downloading and extracting {0}".format(url))
            (tgz, _) = urlretrieve(url, os.path.join(d, self.helper + ".tgz"))
            logger.debug("Extracting {0}".format(tgz))
            with tarfile.open(tgz, "r:gz") as tarf:
                tarf.extractall(path=d)
            try:
                yield d
            finally:
                logger.debug("Cleaning up temporary directory {0}".format(d))

    def apt_install(self, package):
        """Try to use ``apt-get`` to install a package."""
        if not self.PACKAGE_MANAGERS['apt-get']:
            return False
        self._check_call(['sudo', 'apt-get', '-q', 'install', package])
        return True

    def port_install(self, package):
        """Try to use ``port`` to install a package."""
        if not self.PACKAGE_MANAGERS['port']:
            return False
        self._check_call(['sudo', 'port', 'install', package])
        return True

    def yum_install(self, package):
        """Try to use ``yum`` to install a package."""
        if not self.PACKAGE_MANAGERS['yum']:
            return False
        self._check_call(['sudo', 'yum', '--quiet', 'install', package])
        return True

    # Abstract interfaces to be implemented by subclasses

    def install_helper(self):
        """Install the helper program.

        :raise: :exc:`NotImplementedError` as this method must be implemented
          by a concrete subclass.
        """
        if self.find_helper():
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.helper, self.helper_path))
            return
        raise NotImplementedError("Unsure how to install {0}"
                                  .format(self.helper))
