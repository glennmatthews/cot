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

"""Handling of VMDK files."""

import logging
import os
import re

from distutils.version import StrictVersion

from COT.disks.disk import DiskRepresentation
from COT.helpers import helpers, HelperNotFoundError

logger = logging.getLogger(__name__)


class VMDK(DiskRepresentation):
    """VMDK disk image file representation."""

    disk_format = "vmdk"

    @property
    def disk_subformat(self):
        """Disk subformat, such as 'streamOptimized'."""
        if self._disk_subformat is None:
            # Look at the VMDK file header to determine the sub-format
            with open(self.path, 'rb') as f:
                # The header contains a mix of binary and ASCII, so ignore
                # any errors in decoding binary data to strings
                header = f.read(1000).decode('ascii', 'ignore')
                # Detect the VMDK format from the output:
                match = re.search('createType="(.*)"', header)
                if not match:
                    raise RuntimeError(
                        "Could not find VMDK 'createType' in the "
                        "file header:\n{0}".format(header))
                vmdk_format = match.group(1)
            logger.info("VMDK sub-format is '%s'", vmdk_format)
            self._disk_subformat = vmdk_format
        return self._disk_subformat

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
        output_path = os.path.join(output_dir, file_prefix + ".vmdk")
        if output_subformat == "streamOptimized":
            # TODO
            if (helpers['qemu-img'] and
                    helpers['qemu-img'].version >= StrictVersion("2.1.0")):
                helpers['qemu-img'].call(['convert',
                                          '-O', 'vmdk',
                                          '-o', 'subformat=streamOptimized',
                                          input_image.path,
                                          output_path])
            elif helpers['vmdktool']:
                if input_image.disk_format != 'raw':
                    # vmdktool needs a raw image as input
                    from COT.disks import RAW
                    temp_image = RAW.from_other_image(input_image, output_dir)
                    output_image = cls.from_other_image(temp_image,
                                                        output_dir,
                                                        output_subformat)
                    os.remove(temp_image.path)
                    return output_image

                # Note that vmdktool takes its arguments in unusual order -
                # output file comes before input file
                helpers['vmdktool'].call(['-z9',
                                          '-v', output_path,
                                          input_image.path])
            else:
                raise HelperNotFoundError("No helper program available.")
        else:
            raise NotImplementedError("No support for subformat '%s'",
                                      output_subformat)
        return cls(output_path)

    def _create_file(self):
        """Worker function for create_file()."""
        if self._files:
            raise NotImplementedError("Don't know how to create a disk of "
                                      "this format containing a filesystem")
        if self._disk_subformat is None:
            self._disk_subformat = "monolithicSparse"

        helpers['qemu-img'].call(['create', '-f', self.disk_format,
                                  '-o', 'subformat=' + self._disk_subformat,
                                  self.path, self.capacity])
        self._disk_subformat = None
        self._capacity = None
