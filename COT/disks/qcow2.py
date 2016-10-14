# October 2016, Glenn F. Matthews
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

"""Handling of QCOW2 files."""

import os

from COT.disks.disk import DiskRepresentation
from COT.helpers import helpers


class QCOW2(DiskRepresentation):
    """QCOW2 disk image file representation."""

    disk_format = "qcow2"

    @classmethod
    def from_other_image(cls, input_image, output_dir, output_subformat=None):
        """Convert the other disk image into an image of this type.

        :param DiskRepresentation input_image: Existing image representation.
        :param str output_dir: Output directory to store the new image in.
        :param str output_subformat: Any relevant subformat information.
        :rtype: instance of DiskRepresentation or subclass
        """
        file_name = os.path.basename(input_image.path)
        (file_prefix, _) = os.path.splitext(file_name)
        output_path = os.path.join(output_dir, file_prefix + ".qcow2")
        helpers['qemu-img'].call(['convert',
                                  '-O', 'qcow2',
                                  input_image.path,
                                  output_path])
        return cls(output_path)
