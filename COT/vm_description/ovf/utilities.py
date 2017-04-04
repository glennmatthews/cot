#!/usr/bin/env python
#
# utilities.py - Module providing utility functions for OVF/OVA handling
#
# February 2017, Glenn F. Matthews
# Copyright (c) 2013-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Module providing utility functions for OVF and OVA handling.

**Functions**

.. autosummary::
  :nosignatures:

  int_bytes_to_programmatic_units
  parse_manifest
  programmatic_bytes_to_int
"""

import logging
import re

logger = logging.getLogger(__name__)


def parse_manifest(manifest_text):
    r"""Parse the given manifest file contents into a dictionary.

    Args:
      manifest_text (str): Contents of an OVF manifest file

    Returns:
      dict: Mapping of filename to (algorithm, checksum_string)

    Examples:
      ::

        >>> result = parse_manifest(
        ... "SHA1(package.ovf)= 237de026fb285b85528901da058475e56034da95\n"
        ... "SHA1(vmdisk1.vmdk)= 393a66df214e192ffbfedb78528b5be75cc9e1c3\n"
        ... )
        >>> sorted(result.keys())
        ['package.ovf', 'vmdisk1.vmdk']
        >>> result["package.ovf"]
        ('SHA1', '237de026fb285b85528901da058475e56034da95')
        >>> result["vmdisk1.vmdk"]
        ('SHA1', '393a66df214e192ffbfedb78528b5be75cc9e1c3')

    """
    result = {}
    for line in manifest_text.split("\n"):
        if not line:
            continue
        # Per the OVF spec, the correct format for a manifest line is:
        # <algo>(<filename>)= <checksum>
        # but we've seen examples in the wild that aren't quite right, like:
        # <algo> (<filename>)=<checksum>
        # Be forgiving of such errors:
        match = re.match(r"^\s*([A-Z0-9]+)\s*\((.+)\)\s*=\s*([0-9a-f]+)\s*$",
                         line)
        if match:
            result[match.group(2)] = (match.group(1), match.group(3))
        else:
            logger.error('Unexpected or invalid manifest line: "%s"', line)

    return result


def programmatic_bytes_to_int(base_value, programmatic_units):
    """Convert a byte value expressed in programmatic units to the raw number.

    Inverse operation of :func:`int_bytes_to_programmatic_units`.

    .. seealso::
       `DMTF DSP0004, Common Information Model (CIM) Infrastructure
       Specification 2.5
       <http://www.dmtf.org/standards/published_documents/DSP0004_2.5.pdf>`_

    Args:
      base_value (str): Base value string (value of ``ovf:capacity``, etc.)
      programmatic_units (str): Programmatic units string (value of
          ``ovf:capacityAllocationUnits``, etc.)

    Returns:
      int: Number of bytes

    Examples:
      ::

        >>> programmatic_bytes_to_int("128", "byte")
        128
        >>> programmatic_bytes_to_int("1", "byte * 2^10")
        1024
        >>> programmatic_bytes_to_int("128", "byte * 2^20")
        134217728
        >>> programmatic_bytes_to_int("512", "MegaBytes")
        536870912
    """
    if not programmatic_units:
        return int(base_value)

    # programmatic units like 'byte * 2^30'
    match = re.search(r"2\^(\d+)", programmatic_units)
    if match:
        return int(base_value) << int(match.group(1))

    # programmatic units like 'MegaBytes'
    si_prefixes = ["", "kilo", "mega", "giga", "tera"]
    match = re.search("^(.*)bytes$", programmatic_units, re.IGNORECASE)
    if match:
        shift = si_prefixes.index(match.group(1).lower())
        # Technically the correct answer would be:
        #   return int(base_value) * (1000 ** shift)
        # but instead we'll reflect common usage:
        return int(base_value) << (10 * shift)

    if programmatic_units and programmatic_units != 'byte':
        logger.warning("Unknown programmatic units string '%s'",
                       programmatic_units)

    return int(base_value)


def int_bytes_to_programmatic_units(byte_value):
    """Convert a byte count into OVF-style bytes + multiplier.

    Inverse operation of :func:`programmatic_bytes_to_int`

    Args:
      byte_value (int): Number of bytes

    Returns:
      tuple: ``(base_value, programmatic_units)``

    Examples:
      ::

        >>> int_bytes_to_programmatic_units(2147483648)
        ('2', 'byte * 2^30')
        >>> int_bytes_to_programmatic_units(2147483647)
        ('2147483647', 'byte')
        >>> int_bytes_to_programmatic_units(134217728)
        ('128', 'byte * 2^20')
        >>> int_bytes_to_programmatic_units(134217729)
        ('134217729', 'byte')
    """
    shift = 0
    byte_value = int(byte_value)
    while byte_value % 1024 == 0:
        shift += 10
        byte_value /= 1024
    byte_str = str(int(byte_value))
    if shift == 0:
        return (byte_str, "byte")
    return (byte_str, "byte * 2^{0}".format(shift))


if __name__ == "__main__":   # pragma: no cover
    import doctest
    doctest.testmod()
