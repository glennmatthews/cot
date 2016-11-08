# October 2016, Glenn F. Matthews
# Copyright (c) 2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Package for handling various disk file types (VMDK, ISO, QCOW2, etc.).

Tries to provide an API that abstracts away differences in how the
various types need to be operated on (e.g., qemu-img, mkisofs, etc.).

API
---

.. autosummary::
  :nosignatures:

  convert_disk
  create_disk
  disk_representation_from_file
  ~COT.disks.disk.DiskRepresentation

Disk modules
------------

.. autosummary::
  :toctree:

  COT.disks.disk
  COT.disks.iso
  COT.disks.qcow2
  COT.disks.raw
  COT.disks.vmdk
"""

import os

from .iso import ISO
from .qcow2 import QCOW2
from .raw import RAW
from .vmdk import VMDK


_class_for_format = {
    "iso": ISO,
    "vmdk": VMDK,
    "qcow2": QCOW2,
    "raw": RAW,
}


def convert_disk(disk_image, new_directory, new_format, new_subformat=None):
    """Convert a disk representation into a new format.

    Args:
      disk_image (DiskRepresentation): Existing disk image as input.
      new_directory (str): Directory to create new image under
      new_format (str): Format to convert to.
      new_subformat (str): (optional) Sub-format to convert to.

    Returns:
      DiskRepresentation: Converted disk.
    """
    if new_format not in _class_for_format:
        raise NotImplementedError("No support for converting to type '{0}'"
                                  .format(new_format))
    return _class_for_format[new_format].from_other_image(disk_image,
                                                          new_directory,
                                                          new_subformat)


def create_disk(disk_format, *args, **kwargs):
    """Create a disk of the requested format.

    Args:
      disk_format (str): Disk format such as 'iso' or 'vmdk'.

    For the other parameters, see :class:`~COT.disks.disk.DiskRepresentation`.

    Returns:
      DiskRepresentation: Created disk
    """
    if disk_format in _class_for_format:
        return _class_for_format[disk_format](*args, **kwargs)
    raise NotImplementedError("No support for files of type '{0}'"
                              .format(disk_format))


def disk_representation_from_file(file_path):
    """Get a DiskRepresentation appropriate to the given file.

    Args:
      file_path (str): Path of existing file to represent.

    Returns:
      DiskRepresentation: Representation of this file.
    """
    if not os.path.exists(file_path):
        raise IOError(2, "No such file or directory: {0}".format(file_path))
    for cls in [VMDK, QCOW2, ISO, RAW]:
        if cls.file_is_this_type(file_path):
            return cls(path=file_path)
    raise NotImplementedError("No support for files of this type")


__all__ = (
    'convert_disk',
    'create_disk',
    'disk_representation_from_file',
)
