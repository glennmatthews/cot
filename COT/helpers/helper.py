#!/usr/bin/env python
#
# helper.py - Abstract provider of a non-Python helper program.
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2015-2016 the COT project developers.
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
import os
import os.path
import errno
import re
import shutil
import subprocess
import tarfile
from distutils.spawn import find_executable
from distutils.version import StrictVersion

try:
    # Python 3.x
    from tempfile import TemporaryDirectory
except ImportError:
    # Python 2.x
    import tempfile

    @contextlib.contextmanager
    def TemporaryDirectory(suffix='',   # noqa: N802
                           prefix='tmp',
                           dirpath=None):
        """Create a temporary directory and make sure it's deleted later.

        Reimplementation of Python 3's ``tempfile.TemporaryDirectory``.
        """
        tempdir = tempfile.mkdtemp(suffix, prefix, dirpath)
        try:
            yield tempdir
        finally:
            shutil.rmtree(tempdir)

import requests
from verboselogs import VerboseLogger

logging.setLoggerClass(VerboseLogger)
logger = logging.getLogger(__name__)


def guess_file_format_from_path(file_path):
    """Guess the preferred file format based on file path/extension."""
    file_format = os.path.splitext(file_path)[1][1:]
    if not file_format:
        raise RuntimeError(
            "Unable to guess file format from desired filename {0}"
            .format(file_path))
    if file_format == 'img':
        file_format = 'raw'
    logger.debug("Guessed file format is %s", file_format)
    return file_format


class HelperNotFoundError(OSError):
    """A helper program cannot be located."""


class HelperError(EnvironmentError):
    """A helper program exited with non-zero return code."""


class Helper(object):
    """A provider of a non-Python helper program.

    **Class Properties**

    .. autosummary::
      :nosignatures:

      PACKAGE_MANAGERS

    **Class Methods**

    .. autosummary::
      :nosignatures:

      confirm
      apt_install
      port_install
      yum_install
      download_and_expand
      find_executable
      make_install_dir
      install_file

    **Instance Properties**

    .. autosummary::
      name
      path
      version

    **Instance Methods**

    .. autosummary::
      :nosignatures:

      call_helper
      install_helper
    """

    @classmethod
    def confirm(cls, _prompt):
        """Prompt user to confirm the requested operation.

        Default method to be used when COT.helpers is run by itself without
        the broader COT package.
        The COT package will override this with e.g. the CLI.confirm method.

        :param str _prompt: Message to prompt the user with
        :return: ``True`` (user confirms acceptance) or ``False``
                 (user declines)
        """
        return True

    PACKAGE_MANAGERS = {
        "port":    find_executable('port'),
        "apt-get": find_executable('apt-get'),
        "yum":     find_executable('yum'),
    }
    """Class-level lookup for package manager executables."""

    @classmethod
    def find_executable(cls, name):
        """Wrapper for :func:`distutils.spawn.find_executable`."""
        return find_executable(name)

    @classmethod
    @contextlib.contextmanager
    def download_and_expand(cls, url):
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
        with TemporaryDirectory(prefix="cot_helper") as d:
            logger.debug("Temporary directory is %s", d)
            logger.verbose("Downloading and extracting %s", url)
            response = requests.get(url, stream=True)
            tgz = os.path.join(d, 'helper.tgz')
            with open(tgz, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            del response
            logger.debug("Extracting %s", tgz)
            # the "with tarfile.open()..." construct isn't supported in 2.6
            tarf = tarfile.open(tgz, "r:gz")
            try:
                tarf.extractall(path=d)
            finally:
                tarf.close()
            try:
                yield d
            finally:
                logger.debug("Cleaning up temporary directory %s", d)

    _apt_updated = False
    """Whether we have run 'apt-get update' yet."""

    @classmethod
    def apt_install(cls, package):
        """Try to use ``apt-get`` to install a package."""
        if not cls.PACKAGE_MANAGERS['apt-get']:
            return False
        # check if it's already installed
        msg = cls._check_output(['dpkg', '-s', package], require_success=False)
        if re.search('install ok installed', msg):
            return True
        if not cls._apt_updated:
            cls._check_call(['apt-get', '-q', 'update'], retry_with_sudo=True)
            cls._apt_updated = True
        cls._check_call(['apt-get', '-q', 'install', package],
                        retry_with_sudo=True)
        return True

    _port_updated = False
    """Whether we have run 'port selfupdate' yet."""

    @classmethod
    def port_install(cls, package):
        """Try to use ``port`` to install a package."""
        if not cls.PACKAGE_MANAGERS['port']:
            return False
        if not cls._port_updated:
            cls._check_call(['port', 'selfupdate'], retry_with_sudo=True)
            cls._port_updated = True
        cls._check_call(['port', 'install', package], retry_with_sudo=True)
        return True

    @classmethod
    def yum_install(cls, package):
        """Try to use ``yum`` to install a package."""
        if not cls.PACKAGE_MANAGERS['yum']:
            return False
        cls._check_call(['yum', '--quiet', 'install', package],
                        retry_with_sudo=True)
        return True

    @classmethod
    def make_install_dir(cls, directory, permissions=493):    # 493 == 0o755
        """Check whether the given target directory exists, and create if not.

        :param directory: Directory to check/create.
        """
        if os.path.isdir(directory):
            # TODO: permissions check, update permissions if needed
            return True
        elif os.path.exists(directory):
            raise RuntimeError("Path {0} exists but is not a directory!"
                               .format(directory))
        try:
            logger.verbose("Creating directory " + directory)
            os.makedirs(directory, permissions)
            return True
        except OSError as e:
            logger.verbose("Directory %s creation failed, trying sudo",
                           directory)
            try:
                cls._check_call(['sudo', 'mkdir', '-p',
                                 '--mode=%o' % permissions,
                                 directory])
            except HelperError:
                # That failed too - re-raise the original exception
                raise e
            return True

    @classmethod
    def install_file(cls, src, dest):
        """Copy the given src to the given dest, using sudo if needed.

        :param str src: Source path.
        :param str dest: Destination path.
        :return: True
        """
        logger.verbose("Copying %s to %s", src, dest)
        try:
            shutil.copy(src, dest)
        except (OSError, IOError) as e:
            logger.verbose('Installation error, trying sudo.')
            try:
                cls._check_call(['sudo', 'cp', src, dest])
            except HelperError:
                # That failed too - re-raise the original exception
                raise e
        return True

    def __init__(self, name, version_args=None,
                 version_regexp="([0-9.]+"):
        """Initializer.

        :param name: Name of helper executable
        :param list version_args: Args to pass to the helper to
          get its version. Defaults to ``['--version']`` if unset.
        :param version_regexp: Regexp to get the version number from
          the output of the command.
        """
        self._name = name
        self._path = None
        self._version = None
        if not version_args:
            version_args = ['--version']
        self._version_args = version_args
        self._version_regexp = version_regexp

    @property
    def name(self):
        """Name of the helper program."""
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def path(self):
        """Discovered path to the helper."""
        if not self._path:
            logger.verbose("Checking for helper executable %s", self.name)
            self._path = self.find_executable(self.name)
            if self._path:
                logger.verbose("%s is at %s", self.name, self.path)
            else:
                logger.verbose("No path to %s found", self.name)
        return self._path

    @property
    def version(self):
        """Release version of the associated helper program."""
        if self.path and not self._version:
            output = self.call_helper(self._version_args,
                                      require_success=False)
            match = re.search(self._version_regexp, output)
            if not match:
                raise RuntimeError("Unable to find version number in output:"
                                   "\n{0}".format(output))
            self._version = StrictVersion(match.group(1))
        return self._version

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
        if not self.path:
            if not self.confirm("{0} does not appear to be installed.\n"
                                "Try to install it?"
                                .format(self.name)):
                raise HelperNotFoundError(
                    1,
                    "Unable to proceed without helper program '{0}'. "
                    "Please install it and/or check your $PATH."
                    .format(self.name))
            self.install_helper()
        args.insert(0, self.name)
        if capture_output:
            return self._check_output(args, require_success)
        else:
            self._check_call(args, require_success)
            return None

    def should_not_be_installed_but_is(self):
        """Check whether the tool is already installed.

        :return: False, and logs a warning message, if installed
        :return: True, if not installed
        """
        if self.path:
            logger.warning("Tried to install %s -- but it's already available "
                           "at %s!", self.name, self.path)
            return True
        return False

    # Abstract interfaces to be implemented by subclasses

    def install_helper(self):
        """Install the helper program (abstract method).

        :raise: :exc:`NotImplementedError` as this method must be implemented
          by a concrete subclass.
        """
        if self.should_not_be_installed_but_is():
            return
        raise NotImplementedError("Unsure how to install %s", self.name)

    # Private methods

    @classmethod
    def _check_call(cls, args, require_success=True, retry_with_sudo=False,
                    **kwargs):
        """Wrapper for :func:`subprocess.check_call`.

        Unlike :meth:`check_output` below, this does not redirect stdout
        or stderr; all output from the subprocess will be sent to the system
        stdout/stderr as normal.

        :param list args: Command to invoke and its associated args
        :param boolean require_success: If ``False``, do not raise an error
          when the command exits with a return code other than 0
        :param boolean retry_with_sudo: If ``True``, if the command gets
          an exception, prepend ``sudo`` to the command and try again.

        :raise HelperNotFoundError: if the command doesn't exist
          (instead of a :class:`OSError`)
        :raise HelperError: if the command returns a value other than 0 and
          :attr:`require_success` is not ``False``
        :raise OSError: as :func:`subprocess.check_call`.
        """
        cmd = args[0]
        logger.info("Calling '%s'...", " ".join(args))
        try:
            subprocess.check_call(args, **kwargs)
        except OSError as e:
            if retry_with_sudo and (e.errno == errno.EPERM or
                                    e.errno == errno.EACCES):
                cls._check_call(['sudo'] + args,
                                require_success=require_success,
                                retry_with_sudo=False,
                                **kwargs)
                return
            if e.errno != errno.ENOENT:
                raise
            raise HelperNotFoundError(e.errno,
                                      "Unable to locate helper program '{0}'. "
                                      "Please check your $PATH.".format(cmd))
        except subprocess.CalledProcessError as e:
            if require_success:
                if retry_with_sudo:
                    cls._check_call(['sudo'] + args,
                                    require_success=require_success,
                                    retry_with_sudo=False,
                                    **kwargs)
                    return
                raise HelperError(e.returncode,
                                  "Helper program '{0}' exited with error {1}"
                                  .format(cmd, e.returncode))
        logger.info("...done")
        logger.debug("%s exited successfully", cmd)

    @classmethod
    def _check_output(cls, args, require_success=True, **kwargs):
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
        :raise OSError: as :func:`subprocess.check_call`.
        """
        cmd = args[0]
        logger.info("Calling '%s' and capturing its output...", " ".join(args))
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
                          .decode('ascii', 'ignore'))
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
            raise HelperNotFoundError(e.errno,
                                      "Unable to locate helper program '{0}'. "
                                      "Please check your $PATH.".format(cmd))
        except subprocess.CalledProcessError as e:
            try:
                stdout = e.output.decode()
            except AttributeError:
                # CalledProcessError doesn't have 'output' in 2.6
                stdout = u"(output unavailable)"
            if require_success:
                raise HelperError(e.returncode,
                                  "Helper program '{0}' exited with error {1}:"
                                  "\n> {2}\n{3}".format(cmd, e.returncode,
                                                        " ".join(args),
                                                        stdout))
        logger.info("...done")
        logger.verbose("%s output:\n%s", cmd, stdout)
        return stdout
