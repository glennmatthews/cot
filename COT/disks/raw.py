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

"""Handling of raw disk image files."""

import logging
import os
import re

from COT.disks.disk import DiskRepresentation
from COT.helpers import helpers, helper_select

logger = logging.getLogger(__name__)


class RAW(DiskRepresentation):
    """Raw disk image file representation."""

    disk_format = "raw"

    @property
    def files(self):
        """List of files on the FAT32 file system of this disk."""
        if self._files is None and self.path and os.path.exists(self.path):
            output = helpers['fatdisk'].call([self.path, "ls"])
            # Output looks like:
            #
            # -----aD        13706       2016 Aug 04 input.ovf
            # Listed 1 entry
            #
            # where all we really want is the 'input.ovf'
            result = []
            for line in output.split("\n"):
                if not output:
                    continue
                if re.match(r"^Listed", line):
                    continue
                fields = line.split()
                if not fields:
                    continue
                if len(fields) < 6:
                    logger.warning("Unexpected line in 'fatdisk' output: %s",
                                   line)
                    continue
                result.append(fields[5])
            self._files = result
        return self._files

    @classmethod
    def file_is_this_type(cls, path):
        """Whether this file is a RAW image.

        Any file conceivably can be a RAW image; there's no file magic number.

        For the parameters, see :meth:`DiskRepresentation.file_is_this_type`.
        """
        # Any file *could* be a RAW image, so let that be our fallback option,
        # i.e., less than 100% confidence:
        confidence = super(RAW, cls).file_is_this_type(path)
        if confidence == 100:
            confidence = 10
        return confidence

    @classmethod
    def _create_file(cls, path, files=None, capacity=None, **kwargs):
        """Create a raw disk image file.

        Args:
          path (str): Location to create RAW file.
          files (list): List of files to include in a FAT32 filesystem.
          capacity (str): Disk capacity string. If not set, will be calculated
            as just sufficient to include the given ``files``.
          **kwargs: passed through to :meth:`DiskRepresentation._create_file`
        """
        if not files:
            super(RAW, cls)._create_file(path, capacity=capacity, **kwargs)
            return

        if not capacity:
            # What size disk do we need to contain the requested file(s)?
            capacity_val = 0
            for content_file in files:
                capacity_val += os.path.getsize(content_file)
            # Round capacity to the next larger multiple of 8 MB
            # just to be safe...
            capacity_val = int(8 * ((capacity_val / 1024 / 1024 / 8) + 1))
            capacity_str = "{0}M".format(capacity_val)
            capacity = capacity_str
            logger.verbose(
                "To contain files %s, disk capacity of %s will be %s",
                files, path, capacity_str)

        logger.info("Calling fatdisk to create/format a raw disk image")
        helpers['fatdisk'].call([path, 'format', 'size', capacity, 'fat32'])
        for content_file in files:
            logger.verbose("Calling fatdisk to add %s to the image",
                           content_file)
            helpers['fatdisk'].call([path, 'fileadd', content_file,
                                     os.path.basename(content_file)])
        logger.info("All requested files successfully added to %s", path)

    @classmethod
    def from_other_image(cls, input_image, output_dir, output_subformat=None):
        """Convert the other disk image into an image of this type.

        Args:
          input_image (DiskRepresentation): Existing image representation.
          output_dir (str): Output directory to store the new image in.
          output_subformat (str): Any relevant subformat information.

        Returns:
          RAW: representation of newly created raw image.
        """
        file_name = os.path.basename(input_image.path)
        file_prefix, _ = os.path.splitext(file_name)
        output_path = os.path.join(output_dir, file_prefix + ".img")
        if (input_image.disk_format == 'vmdk' and
                input_image.disk_subformat == 'streamOptimized'):
            helper = helper_select([('qemu-img', '1.2.0'), 'vmdktool'])
            # Special case: qemu-img < 1.2.0 can't read streamOptimized VMDKs
            if helper.name == 'vmdktool':
                # Note that vmdktool takes its arguments in unusual order -
                # output file comes before input file
                helper.call(['-s', output_path, input_image.path])
                return cls(output_path)

        helpers['qemu-img'].call(['convert',
                                  '-O', 'raw',
                                  input_image.path,
                                  output_path])
        return cls(output_path)
