#!/usr/bin/env python
#
# utilities.py - General utility functions
#
# February 2017, Glenn F. Matthews
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
"""General-purpose utility functions for COT.

**Functions**

.. autosummary::
  :nosignatures:

  available_bytes_at_path
  directory_size
  pretty_bytes
  tar_entry_size
  to_string
"""

import errno
import logging
import os
import sys

import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def available_bytes_at_path(path):
    """Get the available disk space in a given directory.

    Args:
      path (str): Directory path to check.

    Returns:
      int: Available space, in bytes

    Raises:
      OSError: if the specified path does not exist or is not readable.
    """
    statvfs = os.statvfs(path)
    # available = free blocks times block size
    available = statvfs.f_bavail * statvfs.f_frsize
    logger.debug("There appears to be %s available at %s",
                 pretty_bytes(available), path)
    return available


def directory_size(path):
    """Total bytes consumed by the contents of a directory.

    Args:
      path (str): Directory path

    Returns:
      int: Total bytes consumed by files in this directory.

    Raises:
      OSError: if the specified path does not exist or is not a directory.
    """
    if not os.path.exists(path):
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), path)
    if not os.path.isdir(path):
        raise OSError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), path)
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except OSError as exc:
                logger.debug("Unable to get size of %s (%s), continuing.",
                             filepath, exc.strerror)
    logger.debug("Total disk space consumed by %s is %s",
                 path, pretty_bytes(total_size))
    return total_size


def pretty_bytes(byte_value, base_shift=0):
    """Pretty-print the given bytes value.

    Args:
      byte_value (float): Value
      base_shift (int): Base value of byte_value
            (0 = bytes, 1 = KiB, 2 = MiB, etc.)

    Returns:
      str: Pretty-printed byte string such as "1.00 GiB"

    Examples:
      ::

        >>> pretty_bytes(512)
        '512 B'
        >>> pretty_bytes(512, 2)
        '512 MiB'
        >>> pretty_bytes(65536, 2)
        '64 GiB'
        >>> pretty_bytes(65547)
        '64.01 KiB'
        >>> pretty_bytes(65530, 3)
        '63.99 TiB'
        >>> pretty_bytes(1023850)
        '999.9 KiB'
        >>> pretty_bytes(1024000)
        '1000 KiB'
        >>> pretty_bytes(1048575)
        '1024 KiB'
        >>> pretty_bytes(1049200)
        '1.001 MiB'
        >>> pretty_bytes(2560)
        '2.5 KiB'
        >>> pretty_bytes(.0001, 3)
        '104.9 KiB'
        >>> pretty_bytes(.01, 1)
        '10 B'
        >>> pretty_bytes(.001, 1)
        '1 B'
        >>> pretty_bytes(.0001, 1)
        '0 B'
        >>> pretty_bytes(100, -1)
        Traceback (most recent call last):
            ...
        ValueError: base_shift must not be negative
    """
    if base_shift < 0:
        raise ValueError("base_shift must not be negative")
    tags = ["B", "KiB", "MiB", "GiB", "TiB", 'PiB', 'EiB', 'ZiB', 'YiB']
    byte_value = float(byte_value)
    shift = base_shift
    while byte_value >= 1024.0:
        byte_value /= 1024.0
        shift += 1
    while byte_value < 1.0 and shift > 0:
        byte_value *= 1024.0
        shift -= 1
    # Fractions of a byte should be considered a rounding error:
    if shift == 0:
        byte_value = round(byte_value)
    return "{0:.4g} {1}".format(byte_value, tags[shift])


def tar_entry_size(filesize):
    """The space a file of the given size will actually require in a TAR file.

    The entry has a 512-byte header followd by the actual file data,
    padded to a multiple of 512 bytes if necessary.

    Args:
      filesize (int): File size in bytes

    Returns:
      int: Bytes consumed in a TAR archive by this file.

    Examples:
      ::

        >>> tar_entry_size(1)
        1024
        >>> tar_entry_size(511)
        1024
        >>> tar_entry_size(512)
        1024
        >>> tar_entry_size(513)
        1536
    """
    # round up to next multiple of 512
    return 512 + filesize + ((512 - filesize) % 512)


def to_string(obj):
    """Get string representation of an object, special-case for XML Element.

    Args:
      obj (object): Object to represent as a string.
    Returns:
      str: string representation
    Examples:
      ::

        >>> to_string("Hello")
        'Hello'
        >>> to_string(27.5)
        '27.5'
        >>> e = ET.Element('hello', attrib={'key': 'value'})
        >>> print(e)   # doctest: +ELLIPSIS
        <Element ...hello... at ...>
        >>> print(to_string(e))
        <hello key="value" />
    """
    if ET.iselement(obj):
        if sys.version_info[0] >= 3:
            return ET.tostring(obj, encoding='unicode')
        else:
            return ET.tostring(obj)
    else:
        return str(obj)


if __name__ == "__main__":   # pragma: no cover
    import doctest
    doctest.testmod()
