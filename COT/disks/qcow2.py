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
from COT.helpers import helpers, helper_select


class QCOW2(DiskRepresentation):
    """QCOW2 disk image file representation."""

    disk_format = "qcow2"

    @classmethod
    def from_other_image(cls, input_image, output_dir, output_subformat=None):
        """Convert the other disk image into an image of this type.

        Args:
          input_image (DiskRepresentation): Existing image representation.
          output_dir (str): Output directory to store the new image in.
          output_subformat (str): Any relevant subformat information.

        Returns:
          QCOW2: representation of newly created qcow2 image file
        """
        file_name = os.path.basename(input_image.path)
        (file_prefix, _) = os.path.splitext(file_name)
        output_path = os.path.join(output_dir, file_prefix + ".qcow2")
        if (input_image.disk_format == 'vmdk' and
                input_image.disk_subformat == 'streamOptimized'):
            helper = helper_select([('qemu-img', '1.2.0'), 'vmdktool'])
            # Special case: qemu-img < 1.2.0 can't read streamOptimized VMDKs
            if helper.name == 'vmdktool':
                # vmdktool can convert streamOptimized VMDK to raw
                # Convert vmdk to raw, then raw to qcow2
                # Note that vmdktool takes its arguments in unusual order -
                # output file comes before input file
                from COT.disks import RAW
                try:
                    temp_image = RAW.from_other_image(input_image, output_dir)
                    return cls.from_other_image(temp_image, output_dir,
                                                output_subformat)
                finally:
                    os.remove(temp_image.path)

        helpers['qemu-img'].call(['convert',
                                  '-O', 'qcow2',
                                  input_image.path,
                                  output_path])
        return cls(output_path)
