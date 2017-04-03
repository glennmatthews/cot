#!/usr/bin/env python
#
# helper.py - Abstract provider of a non-Python helper program.
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2015-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Common interface for providers of non-Python helper programs.

Provides the ability to install the program if not already present,
and the ability to run the program as well.

**Classes**

.. autosummary::
  :nosignatures:

  HelperNotFoundError
  HelperError
  Helper
  PackageManager

**Attributes**

.. autosummary::
  :nosignatures:

  helpers

**Functions**

.. autosummary::
  :nosignatures:

  check_call
  check_output
"""

import logging

import os
import os.path
import contextlib
import errno
import platform
import re
import shutil
import subprocess

import tarfile
import distutils.spawn
from distutils.version import StrictVersion
import requests

logger = logging.getLogger(__name__)

try:
    # Python 3.x
    from tempfile import TemporaryDirectory
except ImportError:
    # Python 2.x
    import tempfile

    # pylint: disable=invalid-name
    @contextlib.contextmanager
    def TemporaryDirectory(suffix='',   # noqa: N802
                           prefix='tmp',
                           dirpath=None):
        """Create a temporary directory and make sure it's deleted later.

        Reimplementation of Python 3's ``tempfile.TemporaryDirectory``.
        For the parameters, see :class:`tempfile.TemporaryDirectory`.

        Yields:
          str: Path to temporary directory
        """
        tempdir = tempfile.mkdtemp(suffix, prefix, dirpath)
        try:
            yield tempdir
        finally:
            shutil.rmtree(tempdir)


class HelperNotFoundError(OSError):
    """A helper program cannot be located."""


class HelperError(EnvironmentError):
    """A helper program exited with non-zero return code."""


class HelperDict(dict):
    """Dictionary of Helper objects by name.

    Similar to :class:`collections.defaultdict` but takes the key
    as a parameter to the factory.
    """

    def __init__(self, factory, *args, **kwargs):
        """Create the given dictionary with the given factory class/method.

        Args:
          factory (object): Factory class or method to be called to populate
              a new entry in response to :meth:`__missing__`.

        For the other parameters, see :class:`dict`.
        """
        super(HelperDict, self).__init__(*args, **kwargs)
        self.factory = factory

    def __missing__(self, key):
        """Method called when accessing a non-existent key.

        Automatically populate the given key with an instance of the factory.

        Args:
          key (object): Key that was not yet defined in this dictionary.

        Returns:
          object: Result of calling ``self.factory(key)``
        """
        self[key] = self.factory(key)
        return self[key]


class Helper(object):
    """A provider of a non-Python helper program.

    **Static Methods**

    .. autosummary::
      :nosignatures:

      copy_file
      download_and_expand_tgz
      mkdir

    **Instance Properties**

    .. autosummary::
      name
      info_uri
      installable
      installed
      path
      version

    **Instance Methods**

    .. autosummary::
      :nosignatures:

      call
      install
      _install
      unsure_how_to_install
    """

    def __init__(self, name,
                 info_uri=None,
                 version_args=None,
                 version_regexp="([0-9.]+)"):
        """Initializer.

        Args:
          name (str): Name of helper executable
          info_uri (str): URI to refer to for more info about this helper.
          version_args (list): Args to pass to the helper to
              get its version. Defaults to ``['--version']`` if unset.
          version_regexp (str): Regexp to get the version number from
              the output of the command.
        """
        self._name = name
        self._info_uri = info_uri
        self._path = None
        self._installed = None
        self._version = None
        if not version_args:
            version_args = ['--version']
        self._version_args = version_args
        self._version_regexp = version_regexp
        self.cached_output = {}
        """Cache of call args --> output from this call.

        This is opt-in per-subclass - nothing is cached by default.
        """

    def __bool__(self):
        """A helper is True if installed and False if not installed."""
        return self.installed

    # For Python 2.x compatibility:
    __nonzero__ = __bool__

    _provider_package = {}
    """Mapping of package manager name to package name to install with it."""

    USER_INTERFACE = None
    """User interface (if any) available to helpers."""

    @property
    def name(self):
        """Name of the helper program."""
        return self._name

    @property
    def info_uri(self):
        """URI for more information about this helper."""
        return self._info_uri

    @property
    def path(self):
        """Discovered path to the helper."""
        if not self._path:
            logger.spam("Checking for helper executable %s", self.name)
            self._path = distutils.spawn.find_executable(self.name)
            if self._path:
                logger.debug("%s is at %s", self.name, self.path)
                self._installed = True
            else:
                logger.debug("No path to %s found", self.name)
        return self._path

    @property
    def installed(self):
        """Whether this helper program is installed and available to run."""
        if self._installed is None:
            self._installed = (self.path is not None)
        return self._installed

    @property
    def installable(self):
        """Whether COT is capable of installing this program on this system."""
        for pm_name in self._provider_package:
            if helpers[pm_name]:
                return True
        return False

    @property
    def version(self):
        """Release version of the associated helper program."""
        if self.installed and not self._version:
            output = self.call(self._version_args, require_success=False)
            match = re.search(self._version_regexp, output)
            if not match:
                raise RuntimeError(
                    "Unable to find version number for '{0}' in output from"
                    " '{0} {1}':\n{2}".format(self.name,
                                              ' '.join(self._version_args),
                                              output))
            self._version = StrictVersion(match.group(1))
        return self._version

    def call(self, args,
             capture_output=True,
             use_cached=True,
             **kwargs):
        """Call the helper program with the given arguments.

        Args:
          args (tuple): List of arguments to the helper program.
          capture_output (boolean): If ``True``, stdout/stderr will be
            redirected to a buffer and returned, instead of being displayed
            to the user. (I.e., :func:`check_output` will be invoked
            instead of :func:`check_call`)
          use_cached (boolean): If ``True``, and ``capture_output`` is also
             ``True``, then if there is an entry in :attr:`cached_output`
             for the given ``args``, just return that entry instead of
             calling the helper again.
             Ignored if ``capture_output`` is ``False``.

        .. note::
          By default no captured output is cached (as it may not necessarily
          be appropriate to cache the output of many commands.) Subclasses
          that wish to cache output of certain calls should wrap this method
          with the appropriate logic, typically along the lines of::

              output = super(MyHelper, self).call(args, *kwargs)
              if output and args[0] == 'info':
                  self.cached_output[args] = output
              return output

        Returns:
          str: Captured stdout/stderr if :attr:`capture_output` is True,
          else ``None``.

        For the other parameters, see :func:`check_call` and
        :func:`check_output`.

        Raises:
          HelperNotFoundError: if the helper was not previously
              installed, and the user declines to install it at this time.
        """
        if not self.path:
            if self.USER_INTERFACE and not self.USER_INTERFACE.confirm(
                    "{0} does not appear to be installed.\nTry to install it?"
                    .format(self.name)):
                raise HelperNotFoundError(
                    1,
                    "Unable to proceed without helper program '{0}'. "
                    "Please install it and/or check your $PATH."
                    .format(self.name))
            self.install()
        # Force args to be a tuple if it was a list,
        # as tuple is hashable for the cache and list is not.
        args = tuple(args)
        call_args = [self.name] + list(args)
        if capture_output:
            if use_cached and args in self.cached_output:
                logger.debug("Returning cached output of '%s'",
                             " ".join(call_args))
                logger.spam("Cached output:\n%s",
                            self.cached_output[args])
                return self.cached_output[args]
            # Default implementation does not cache any output.
            # Subclasses should wrap this method if they want to
            # cache output from specific commands.
            return check_output(call_args, **kwargs)
        else:
            check_call(call_args, **kwargs)
            return None

    def install(self):
        """Install the helper program.

        Raises:
          NotImplementedError: if not :attr:`installable` on this platform
          RuntimeError: if potentially :attr:`installable` on this platform
            but required helpers (e.g., package managers) are not available.
          HelperError: if installation is attempted but fails.

        Subclasses should not override this method but instead should provide
        an appropriate implementation of the :meth:`_install` method.
        """
        if self.installed:
            return
        if not self.installable:
            raise self.unsure_how_to_install()
        logger.notice("Installing '%s'...", self.name)
        # Call the subclass implementation
        self._install()
        # Make sure it actually performed as promised
        if not self.path:
            raise HelperNotFoundError(
                1,
                "Installation did not raise an exception, but afterward, "
                "unable to locate {0}!".format(self.name))

        logger.notice("Successfully installed '%s'", self.name)

    def unsure_how_to_install(self):
        """Return a RuntimeError or NotImplementedError for install trouble."""
        msg = "Unsure how to install {0}.".format(self.name)
        if self.info_uri:
            msg += "\nRefer to {0} for information".format(self.info_uri)

        if platform.system() == 'Darwin':
            if 'brew' in self._provider_package and not helpers['brew']:
                msg += ("\nCOT can use Homebrew (https://brew.sh), "
                        "if available on your system, to install {0}."
                        .format(self.name))
            if 'port' in self._provider_package and not helpers['port']:
                msg += ("\nCOT can use MacPorts (https://www.macports.org/), "
                        "if available on your system, to install {0}."
                        .format(self.name))
            if ('brew' in self._provider_package or
                    'port' in self._provider_package):
                return RuntimeError(msg)
            else:
                return NotImplementedError(msg)
        elif platform.system() == 'Linux' and (
                ('apt-get' in self._provider_package or
                 'yum' in self._provider_package) and
                not (helpers['apt-get'] or helpers['yum'])):
            msg += ("\nCOT can use package managers 'yum' or 'apt-get' to"
                    " install helpers on your system, but it appears that"
                    " you have neither of these package managers?")
            return RuntimeError(msg)
        else:
            return NotImplementedError(msg)

    def _install(self):
        """Subclass-specific implementation of installation logic.

        This method should only be called from :meth:`install`,
        which does the appropriate pre-validation against the
        :attr:`installed` and :attr:`installable` properties before
        calling into this method if appropriate.
        """
        # Default implementation
        for pm_name, package in self._provider_package.items():
            if helpers[pm_name]:
                helpers[pm_name].install_package(package)
                return
        raise self.unsure_how_to_install()

    @staticmethod
    @contextlib.contextmanager
    def download_and_expand_tgz(url):
        """Context manager for downloading and expanding a .tar.gz file.

        Creates a temporary directory, downloads the specified URL into
        the directory, unzips and untars the file into this directory,
        then yields to the given block. When the block exits, the temporary
        directory and its contents are deleted.

        ::

          with download_and_expand_tgz("http://example.com/foo.tgz") as d:
              # archive contents have been extracted to 'd'
              ...
          # d is automatically cleaned up.

        Args:
          url (str): URL of a .tgz or .tar.gz file to download.

        Yields:
          str: Temporary directory path where the archive has been extracted.
        """
        with TemporaryDirectory(prefix="cot_helper") as directory:
            logger.debug("Temporary directory is %s", directory)
            logger.verbose("Downloading and extracting %s", url)
            response = requests.get(url, stream=True)
            tgz = os.path.join(directory, 'helper.tgz')
            with open(tgz, 'wb') as fileobj:
                shutil.copyfileobj(response.raw, fileobj)
            del response
            logger.debug("Extracting %s", tgz)
            with tarfile.open(tgz, "r:gz") as tarf:
                tarf.extractall(path=directory)
            try:
                yield directory
            finally:
                logger.debug("Cleaning up temporary directory %s", directory)

    @staticmethod
    def mkdir(directory, permissions=493):    # 493 == 0o755
        """Check whether the given target directory exists, and create if not.

        Args:
          directory (str): Directory to check/create.
          permissions (int): Permission mask to set when creating a directory.
              Default is ``0o755``.
        """
        if os.path.isdir(directory):
            # TODO: permissions check, update permissions if needed
            return True
        elif os.path.exists(directory):
            raise RuntimeError("Path {0} exists but is not a directory!"
                               .format(directory))
        try:
            logger.debug("Creating directory " + directory)
            os.makedirs(directory, permissions)
            return True
        except OSError as exc:
            logger.debug("Directory %s creation failed, trying sudo",
                         directory)
            try:
                check_call(['sudo', 'mkdir', '-p',
                            # We previously used '--mode' but OS X lacks it.
                            '-m', '%o' % permissions,
                            directory])
            except HelperError:
                # That failed too - re-raise the original exception
                raise exc
            return True

    @staticmethod
    def copy_file(src, dest):
        """Copy the given src to the given dest, using sudo if needed.

        Args:
          src (str): Source path.
          dest (str): Destination path.

        Returns:
          bool: True

        Raises:
          HelperError: if file copying fails
        """
        logger.debug("Copying %s to %s", src, dest)
        try:
            shutil.copy(src, dest)
        except (OSError, IOError) as exc:
            logger.debug('Installation error, trying sudo.')
            try:
                check_call(['sudo', 'cp', src, dest])
            except HelperError:
                # That failed too - re-raise the original exception
                raise exc
        return True


helpers = HelperDict(Helper)   # pylint: disable=invalid-name
"""Dictionary of concrete Helper subclasses to be populated at load time."""


class PackageManager(Helper):
    """Helper program with additional API method install_package()."""

    def install_package(self, package):
        """Install the requested package if needed.

        Args:
          package (str): Name of the package to install, or a list of
            parameters used to install the package.
        """
        raise NotImplementedError("install_package not implemented!")


def check_call(args, require_success=True, retry_with_sudo=False, **kwargs):
    """Wrapper for :func:`subprocess.check_call`.

    Unlike :meth:`check_output` below, this does not redirect stdout
    or stderr; all output from the subprocess will be sent to the system
    stdout/stderr as normal.

    Args:
      args (list): Command to invoke and its associated args
      require_success (boolean): If ``False``, do not raise an error when the
          command exits with a return code other than 0
      retry_with_sudo (boolean): If ``True``, if the command gets
          an exception, prepend ``sudo`` to the command and try again.

    For the other parameters, see :func:`subprocess.check_call`.

    Raises:
      HelperNotFoundError: if the command doesn't exist (instead of a
          :class:`OSError`)
      HelperError: if :attr:`require_success` is not ``False`` and the command
          returns a value other than 0 (instead of a
          :class:`subprocess.CalledProcessError`).
      OSError: as :func:`subprocess.check_call`.

    Examples:
      ::

        >>> check_call(['true'])
        >>> try:
        ...     check_call(['false'])
        ... except HelperError as e:
        ...     print(e.errno)
        ...     print(e.strerror)
        1
        Helper program 'false' exited with error 1
        >>> check_call(['false'], require_success=False)
        >>> try:
        ...     check_call(['/non/exist'])
        ... except HelperNotFoundError as e:
        ...     print(e.errno)
        ...     print(e.strerror)
        2
        Unable to locate helper program '/non/exist'. Please check your $PATH.
        >>> try:
        ...     check_call(['/etc/'])
        ... except OSError as e:
        ...     print(e.errno)
        ...     print(e.strerror)
        13
        Permission denied
    """
    cmd = args[0]
    # As this call will output to stdout/stderr, make sure the user knows
    # what's about to happen
    logger.notice("Calling '%s'...", " ".join(args))
    try:
        subprocess.check_call(args, **kwargs)
    except OSError as exc:
        if retry_with_sudo and (exc.errno == errno.EPERM or
                                exc.errno == errno.EACCES):
            check_call(['sudo'] + args,
                       require_success=require_success,
                       retry_with_sudo=False,
                       **kwargs)
            return
        # In Travis CI container environment, 'sudo' is disallowed.
        # For some reason, recently (4/2017) it's changed from failing with
        # EPERM "sudo: must be setuid root"
        # to:
        # ENOEXEC "Exec format error"
        # We shouldn't see ENOEXEC otherwise, so we special case this.
        if (exc.errno == errno.ENOEXEC and
                args[0] == 'sudo'):    # pragma: no cover
            raise HelperError(exc.errno, "The 'sudo' command is unavailable")
        if exc.errno != errno.ENOENT:
            raise
        raise HelperNotFoundError(exc.errno,
                                  "Unable to locate helper program '{0}'. "
                                  "Please check your $PATH.".format(cmd))
    except subprocess.CalledProcessError as exc:
        if require_success:
            if retry_with_sudo:
                check_call(['sudo'] + args,
                           require_success=require_success,
                           retry_with_sudo=False,
                           **kwargs)
                return
            raise HelperError(exc.returncode,
                              "Helper program '{0}' exited with error {1}"
                              .format(cmd, exc.returncode))
    logger.notice("...done")
    logger.debug("%s exited successfully", cmd)


def check_output(args, require_success=True, retry_with_sudo=False, **kwargs):
    r"""Wrapper for :func:`subprocess.check_output`.

    Automatically redirects stderr to stdout, captures both to a buffer,
    and generates a debug message with the stdout contents.

    Args:
      args (list): Command to invoke and its associated args
      require_success (boolean): If ``False``, do not raise an error when the
          command exits with a return code other than 0
      retry_with_sudo (boolean): If ``True``, if the command gets an
          exception, prepend ``sudo`` to the command and try again.

    For the other parameters, see :func:`subprocess.check_output`.

    Returns:
      str: Captured stdout/stderr from the command

    Raises:
      HelperNotFoundError: if the command doesn't exist (instead of a
          :class:`OSError`)
      HelperError: if :attr:`require_success` is not ``False`` and the command
          returns a value other than 0 (instead of a
          :class:`subprocess.CalledProcessError`).
      OSError: as :func:`subprocess.check_output`.

    Examples:
      ::

        >>> output = check_output(['echo', 'Hello world!'])
        >>> assert output == "Hello world!\n"
        >>> try:
        ...     check_output(['false'])
        ... except HelperError as e:
        ...     print(e.errno)
        ...     print(e.strerror)
        1
        Helper program 'false' exited with error 1:
        > false
        <BLANKLINE>
        >>> output = check_output(['false'], require_success=False)
        >>> assert output == ''
        >>> try:
        ...     check_output(['/non/exist'])
        ... except HelperNotFoundError as e:
        ...     print(e.errno)
        ...     print(e.strerror)
        2
        Unable to locate helper program '/non/exist'. Please check your $PATH.
        >>> try:
        ...     check_output(['/etc/'])
        ... except OSError as e:
        ...     print(e.errno)
        ...     print(e.strerror)
        13
        Permission denied
    """
    cmd = args[0]
    # Unlike check_call above, here we capture stderr/stdout, so it's
    # much less important to notify the user about this.
    logger.debug("Calling '%s' and capturing its output...", " ".join(args))
    try:
        stdout = subprocess.check_output(args,
                                         stderr=subprocess.STDOUT,
                                         **kwargs).decode('ascii', 'ignore')
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise
        raise HelperNotFoundError(exc.errno,
                                  "Unable to locate helper program '{0}'. "
                                  "Please check your $PATH.".format(cmd))
    except subprocess.CalledProcessError as exc:
        stdout = exc.output.decode()
        if require_success:
            if retry_with_sudo:
                return check_output(['sudo'] + args,
                                    require_success=require_success,
                                    retry_with_sudo=False,
                                    **kwargs)
            raise HelperError(exc.returncode,
                              "Helper program '{0}' exited with error {1}:"
                              "\n> {2}\n{3}".format(cmd, exc.returncode,
                                                    " ".join(args),
                                                    stdout))
    logger.debug("...done")
    logger.spam("%s output:\n%s", cmd, stdout)
    return stdout


def helper_select(choices):
    """Select the first helper that is available from the given list.

    If no helper in the list is currently installed, will install the
    first installable helper from the list.

    Raises:
      HelperNotFoundError: if no valid helper is available or installable.

    Args:
      choices (list): List of helpers, in order from most preferred to
          least preferred. Each choice in this list can be either:

          * a string (the helper name, such as "mkisofs")
          * a tuple of (name, minimum version) such as ("qemu-img", "2.1.0").

    Returns:
      Helper: The selected helper class instance.
    """
    def _name_min_ver_from_choice(choice):
        if isinstance(choice, str):
            # Helper name only, no version constraints
            name = choice
            min_version = None
        else:
            # Tuple of (name, version)
            (name, vers) = choice
            min_version = StrictVersion(vers)

        return (name, min_version)

    for choice in choices:
        name, min_version = _name_min_ver_from_choice(choice)
        if helpers[name]:
            if min_version is None or helpers[name].version >= min_version:
                return helpers[name]

    # OK, nothing yet installed. So what can we install?
    for choice in choices:
        name, min_version = _name_min_ver_from_choice(choice)
        if helpers[name].installable:
            helpers[name].install()
            if min_version is None or helpers[name].version >= min_version:
                return helpers[name]

    msg = "No helper in list {0} is available or installable!".format(choices)

    for choice in choices:
        name, _ = _name_min_ver_from_choice(choice)
        msg += "\n" + str(helpers[name].unsure_how_to_install())

    raise HelperNotFoundError(msg)


if __name__ == "__main__":   # pragma: no cover
    import doctest
    doctest.testmod()
