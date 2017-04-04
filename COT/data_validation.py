#!/usr/bin/env python
#
# data_validation.py - Helper libraries to validate data sanity
#
# September 2013, Glenn F. Matthews
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

"""Various helpers for data sanity checks.

**Exceptions**

.. autosummary::
  :nosignatures:

  InvalidInputError
  ValueMismatchError
  ValueUnsupportedError
  ValueTooLowError
  ValueTooHighError

**Functions**

.. autosummary::
  :nosignatures:

  alphanum_split
  canonicalize_helper
  canonicalize_ide_subtype
  canonicalize_nic_subtype
  canonicalize_scsi_subtype
  check_for_conflict
  device_address
  file_checksum
  mac_address
  match_or_die
  natural_sort
  no_whitespace
  non_negative_int
  positive_int
  validate_int
  truth_value

**Constants**

.. autosummary::
  NIC_TYPES
"""

import hashlib
import re
from collections import namedtuple
from distutils.util import strtobool

from COT.utilities import to_string


def alphanum_split(key):
    """Split the key into a list of [text, int, text, int, ..., text].

    Args:
      key (str): String to split.
    Returns:
      list: List of tokens
    Examples:
      ::

        >>> alphanum_split("hello1world27")
        ['hello', 1, 'world', 27, '']
        >>> alphanum_split("1istheloneliestnumber")
        ['', 1, 'istheloneliestnumber']
    """
    def text_to_int(text):
        """Convert number strings to ints, leave other strings as text.

        Args:
          text (object): Input to convert (str or int)
        Returns:
          object: Converted value (str or int)
        """
        return int(text) if text.isdigit() else text

    return [text_to_int(c) for c in re.split('([0-9]+)', key)]


def natural_sort(iterable):
    """Sort the given list "naturally" rather than in ASCII order.

    E.g, "10" comes after "9" rather than between "1" and "2".

    See also http://nedbatchelder.com/blog/200712/human_sorting.html

    Args:
      iterable (list): List to sort
    Returns:
      list: Sorted list
    Examples:
      ::

        >>> natural_sort(["Eth3", "Eth1", "Eth10", "Eth2"])
        ['Eth1', 'Eth2', 'Eth3', 'Eth10']
        >>> natural_sort(["3rd", "1st", "10th", "101st"])
        ['1st', '3rd', '10th', '101st']
    """
    # Sort based on alphanum_split return value
    return sorted(iterable, key=alphanum_split)


def match_or_die(first_label, first, second_label, second):
    """Make sure "first" and "second" are equal or raise an error.

    Args:
      first_label (str): Descriptive label for :attr:`first`
      first (object): First object to compare
      second_label (str): Descriptive label for :attr:`second`
      second (object): Second object to compare
    Raises:
      ValueMismatchError: if ``first != second``
    Examples:
      ::

        >>> try:
        ...     match_or_die("old", 1, "new", 2)
        ... except ValueMismatchError as e:
        ...     print(e)
        old 1 does not match new 2
    """
    if first != second:
        raise ValueMismatchError("{0} {1} does not match {2} {3}"
                                 .format(first_label,
                                         to_string(first),
                                         second_label,
                                         to_string(second)))


def canonicalize_helper(label, user_input, mappings, re_flags=0):
    """Try to find a mapping of input to output.

    Args:
      label (str): Label to use in any error raised
      user_input (str): User-provided string
      mappings (list): List of ``(expr, canonical)`` pairs for mapping.
      re_flags (int): ``re.IGNORECASE``, etc. if desired
    Returns:
      str: The canonical string
    Raises:
      ValueUnsupportedError: If no ``expr`` in ``mappings`` matches the given
          ``user_input``.
    """
    if user_input is None or user_input == "":
        return None
    for (expr, canonical) in mappings:
        if re.match(expr, user_input, flags=re_flags):
            return canonical
    raise ValueUnsupportedError(label, user_input, [c for (_, c) in mappings])


def canonicalize_ide_subtype(subtype):
    """Try to convert the given IDE controller string to a canonical form.

    Args:
      subtype (str): User-provided string
    Returns:
      str: The canonical string, one of:

      - ``PIIX4``
      - ``virtio``

    Raises:
      ValueUnsupportedError: If the canonical string cannot be determined
    Examples:
      ::

        >>> canonicalize_ide_subtype('VirtIO')
        'virtio'
        >>> canonicalize_ide_subtype('PIIX4')
        'PIIX4'
        >>> try:  # doctest: +ELLIPSIS
        ...     canonicalize_ide_subtype('usb')
        ... except ValueUnsupportedError as e:
        ...     print(e)
        Unsupported value 'usb' for IDE controller subtype...
    """
    return canonicalize_helper("IDE controller subtype", subtype,
                               [
                                   ("piix4", 'PIIX4'),
                                   ("virtio", 'virtio'),
                               ],
                               re.IGNORECASE)


_NIC_MAPPINGS = [
    ("e1000e", 'E1000e'),
    ("e1000", 'E1000'),
    ("pcnet32", 'PCNet32'),
    ("virtio", 'virtio'),
    ("vmxnet *3", 'VMXNET3'),
]

NIC_TYPES = [m[1] for m in _NIC_MAPPINGS]
"""List of NIC type strings recognized as canonical."""


def canonicalize_nic_subtype(subtype):
    """Try to convert the given NIC subtype string to a canonical form.

    Args:
      subtype (str): User-provided string
    Returns:
      str: The canonical string, one of :data:`NIC_TYPES`
    Raises:
      ValueUnsupportedError: If the canonical string cannot be determined
    Examples:
      ::

        >>> canonicalize_nic_subtype('e1000')
        'E1000'
        >>> canonicalize_nic_subtype('vmxnet 3')
        'VMXNET3'
        >>> try:  # doctest: +ELLIPSIS
        ...     canonicalize_nic_subtype('foobar')
        ... except ValueUnsupportedError as e:
        ...     print(e)
        Unsupported value 'foobar' for NIC subtype ...

    .. seealso::
       :meth:`COT.platforms.Platform.validate_nic_type`
    """
    return canonicalize_helper("NIC subtype", subtype,
                               _NIC_MAPPINGS, re.IGNORECASE)


def canonicalize_scsi_subtype(subtype):
    """Try to convert the given SCSI controller string to a canonical form.

    Args:
      subtype (str): User-provided string
    Returns:
      str: The canonical string, one of:

      - ``buslogic``
      - ``lsilogic``
      - ``lsilogicsas``
      - ``virtio``
      - ``VirtualSCSI``

    Raises:
      ValueUnsupportedError: If the canonical string cannot be determined
    Examples:
      ::

        >>> canonicalize_scsi_subtype('LSI Logic')
        'lsilogic'
        >>> canonicalize_scsi_subtype('VirtIO')
        'virtio'
        >>> try:  # doctest: +ELLIPSIS
        ...     canonicalize_scsi_subtype('baz')
        ... except ValueUnsupportedError as e:
        ...     print(e)
        Unsupported value 'baz' for SCSI controller subtype...
    """
    return canonicalize_helper("SCSI controller subtype", subtype,
                               [
                                   ("bus *logic", 'buslogic'),
                                   ("lsi *logic *sas", 'lsilogicsas'),
                                   ("lsi *logic", 'lsilogic'),
                                   ("virtio", 'virtio'),
                                   ("virtual *scsi", 'VirtualSCSI'),
                               ],
                               re.IGNORECASE)


def check_for_conflict(label, refs):
    """Make sure the list does not contain references to more than one object.

    Args:
      label (str): Descriptive label to be used if an error is raised
      refs (list): List of object references (which may include ``None``)
    Raises:
      ValueMismatchError: if references differ
    Returns:
      object: the object or ``None``
    Examples:
      ::

        >>> check_for_conflict("example", ['foo', None, 'foo'])
        'foo'
        >>> try:
        ...     check_for_conflict("conflict", [None, 'foo', 'bar'])
        ... except ValueMismatchError as e:
        ...     print(e)
        Found multiple candidates for the conflict:
        foo
        ...and...
        bar
        Please correct or clarify your search parameters.
    """
    obj = None
    for index, obj1 in enumerate(refs):
        if obj1 is None:
            continue
        for obj2 in refs[(index+1):]:
            if obj2 is not None and obj1 != obj2:
                raise ValueMismatchError(
                    "Found multiple candidates for the {0}:"
                    "\n{1}\n...and...\n{2}\nPlease correct or clarify "
                    "your search parameters."
                    .format(label, to_string(obj1), to_string(obj2)))
        obj = obj1
    return obj


def file_checksum(path_or_obj, checksum_type):
    """Get the checksum of the given file.

    Args:
      path_or_obj (str): File path to checksum OR an opened file object
      checksum_type (str): Supported values are 'md5', 'sha1', 'sha256'.
    Returns:
      str: Hexadecimal file checksum
    """
    # pylint: disable=redefined-variable-type
    if checksum_type == 'md5':
        hash_obj = hashlib.md5()
    elif checksum_type == 'sha1':
        hash_obj = hashlib.sha1()
    elif checksum_type == 'sha256':
        hash_obj = hashlib.sha256()
    else:
        raise NotImplementedError(
            "No support for generating checksum type {0}"
            .format(checksum_type))

    # Is it a file or do we need to open it?
    try:
        path_or_obj.read(0)
        file_obj = path_or_obj
    except AttributeError:
        file_obj = open(path_or_obj, 'rb')

    blocksize = 65536

    try:
        while True:
            buf = file_obj.read(blocksize)
            if len(buf) == 0:
                break
            hash_obj.update(buf)
    finally:
        if file_obj != path_or_obj:
            file_obj.close()

    return hash_obj.hexdigest()


def mac_address(string):
    """Parser helper function for MAC address arguments.

    Validate whether a string is a valid MAC address.
    Recognized formats are:

    * xx:xx:xx:xx:xx:xx
    * xx-xx-xx-xx-xx-xx
    * xxxx.xxxx.xxxx

    Args:
      string (str): String to validate
    Raises:
      InvalidInputError: if string is not a valid MAC address
    Returns:
      str: Validated string(with leading/trailing whitespace stripped)
    """
    string = string.strip()
    if not (re.match(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", string) or
            re.match(r"([0-9a-fA-F]{2}-){5}[0-9a-fA-F]{2}$", string) or
            re.match(r"([0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}$", string)):
        raise InvalidInputError("'{0}' is not a valid MAC address"
                                .format(string))
    # TODO - reformat string to a consistent output style?
    return string


def device_address(string):
    r"""Parser helper function for device address arguments.

    Validate string is an appropriately formed device address such as '1:0'.

    Args:
      string (str): String to validate
    Raises:
      InvalidInputError: if string is not a well-formatted device address
    Returns:
      str: Validated string (with leading/trailing whitespace stripped)
    Examples:
      ::

        >>> device_address("  1:0\n")
        '1:0'
        >>> try:
        ...     device_address("1:0:1")
        ... except InvalidInputError as e:
        ...     print(e)
        '1:0:1' is not a valid device address
    """
    string = string.strip()
    if not re.match(r"\d+:\d+$", string):
        raise InvalidInputError("'{0}' is not a valid device address"
                                .format(string))
    return string


def no_whitespace(string):
    """Parser helper function for arguments not allowed to contain whitespace.

    Args:
      string (str): String to validate
    Raises:
      InvalidInputError: if string contains internal whitespace
    Returns:
      str: Validated string (with leading/trailing whitespace stripped)
    Examples:
      ::

        >>> no_whitespace("    hello    ")
        'hello'
        >>> try:
        ...     no_whitespace('hello world')
        ... except InvalidInputError as e:
        ...     print(e)
        'hello world' contains invalid whitespace
    """
    string = string.strip()
    if len(string.split()) > 1:
        raise InvalidInputError("'{0}' contains invalid whitespace"
                                .format(string))
    return string


def validate_int(string,
                 minimum=None, maximum=None,
                 label=None):
    """Parser helper function for validating integer arguments in a range.

    Args:
      string (str): String to convert to an integer and validate
      minimum (int): Minimum valid value (optional)
      maximum (int): Maximum valid value (optional)
      label (str): Label to include in any errors raised

    Returns:
      int: Validated integer value

    Raises:
      ValueUnsupportedError: if :attr:`string` can't be converted to int
      ValueTooLowError: if value is less than :attr:`minimum`
      ValueTooHighError: if value is more than :attr:`maximum`

    Examples:
      ::

        >>> validate_int('1')
        1
        >>> try:
        ...     validate_int('foo', label='x')
        ... except ValueUnsupportedError as e:
        ...     print(e)
        Unsupported value 'foo' for x - expected integer
        >>> try:
        ...     validate_int('100', label='x', maximum=10)
        ... except ValueTooHighError as e:
        ...     print(e)
        Value '100' for x is too high - must be at most 10
    """
    if label is None:
        label = "input"
    try:
        value = int(string)
    except ValueError:
        raise ValueUnsupportedError(label, string, "integer")
    if minimum is not None and value < minimum:
        raise ValueTooLowError(label, value, minimum)
    if maximum is not None and value > maximum:
        raise ValueTooHighError(label, value, maximum)
    return value


def non_negative_int(string, label=None):
    """Parser helper function for integer arguments that must be 0 or more.

    Alias for :func:`validate_int` setting :attr:`minimum` to 0.

    Args:
      string (str): String to validate.
      label (str): Label to include in any errors raised
    Returns:
      int: Validated integer value
    Raises:
      ValueUnsupportedError: if :attr:`string` can't be converted to int
      ValueTooLowError: if value is less than 0
    Examples:
      ::

        >>> non_negative_int('0')
        0
        >>> non_negative_int('1000')
        1000
        >>> try:
        ...     non_negative_int('-1')
        ... except ValueTooLowError as e:
        ...     print(e)
        Value '-1' for input is too low - must be at least 0
    """
    return validate_int(string, minimum=0, label=label)


def positive_int(string, label=None):
    """Parser helper function for integer arguments that must be 1 or more.

    Alias for :func:`validate_int` setting :attr:`minimum` to 1.

    Args:
      string (str): String to validate.
      label (str): Label to include in any errors raised
    Returns:
      int: Validated integer value
    Raises:
      ValueUnsupportedError: if :attr:`string` can't be converted to int
      ValueTooLowError: if value is less than 1
    Examples:
      ::

        >>> positive_int('1')
        1
        >>> try:
        ...     positive_int('0')
        ... except ValueTooLowError as e:
        ...     print(e)
        Value '0' for input is too low - must be at least 1
    """
    return validate_int(string, minimum=1, label=label)


def truth_value(value):
    """Parser helper function for truth values like '0', 'y', or 'false'.

    Makes use of :func:`distutils.util.strtobool`, but returns True/False
    rather than 1/0.

    Args:
      value (str): String to parse/validate
    Returns:
      bool: True or False
    Raises:
      ValueUnsupportedError: if the value can't be parsed to a boolean.
    Examples:
      ::

        >>> truth_value('y')
        True
        >>> truth_value('false')
        False
        >>> truth_value(True)
        True
        >>> try:    # doctest: +ELLIPSIS
        ...     truth_value('foo')
        ... except ValueUnsupportedError as e:
        ...     print(e)
        Unsupported value 'foo' for truth value - expected ['y', ...
    """
    if isinstance(value, bool):
        return value
    try:
        # Despite its name, strtobool returns 1 or 0 not True or False
        return bool(strtobool(value))
    except ValueError:
        raise ValueUnsupportedError(
            "truth value",
            value,
            ['y', 'yes', 't', 'true', 'on', 1,
             'n', 'no', 'f', 'false', 'off', 0]
        )


ValidRange = namedtuple('ValidRange', ['minimum', 'maximum'])
"""Simple helper class representing a range of valid values."""


# Some handy exception and error types we can throw
class ValueMismatchError(ValueError):
    """Values which were expected to be equal turned out to be not equal."""

    pass


class InvalidInputError(ValueError):
    """Miscellaneous error during validation of user input."""

    pass


class ValueUnsupportedError(InvalidInputError):
    """An unsupported value was provided.

    Args:
      value_type (str): descriptive string
      actual_value (str): invalid value that was provided
      expected_value (object): expected/valid value(s) (item or list)
    """

    def __init__(self, value_type, actual_value, expected_value):
        """Create an instance of this class."""
        self.value_type = value_type
        self.actual_value = actual_value
        self.expected_value = expected_value
        super(ValueUnsupportedError, self).__init__(str(self))

    def __str__(self):
        """Human-readable string representation."""
        return ("Unsupported value '{0}' for {1} - expected {2}"
                .format(self.actual_value, self.value_type,
                        self.expected_value))


class ValueTooLowError(ValueUnsupportedError):
    """A numerical input was less than the lowest supported value.

    Args:
      value_type (str): descriptive string
      actual_value (int): invalid value that was provided
      expected_value (int): minimum supported value
    """

    def __str__(self):
        """Human-readable string representation."""
        return ("Value '{0}' for {1} is too low - must be at least {2}"
                .format(self.actual_value, self.value_type,
                        self.expected_value))


class ValueTooHighError(ValueUnsupportedError):
    """A numerical input was higher than the highest supported value.

    Args:
      value_type (str): descriptive string
      actual_value (int): invalid value that was provided
      expected_value (int): maximum supported value
    """

    def __str__(self):
        """Human-readable string representation."""
        return ("Value '{0}' for {1} is too high - must be at most {2}"
                .format(self.actual_value, self.value_type,
                        self.expected_value))


if __name__ == "__main__":   # pragma: no cover
    import doctest
    doctest.testmod()
