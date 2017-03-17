# October 2016, Glenn F. Matthews
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

"""Handling of VMDK files."""

import logging
import os
import re

from distutils.version import StrictVersion

from COT.disks.disk import DiskRepresentation
from COT.helpers import helpers, helper_select

logger = logging.getLogger(__name__)


class VMDK(DiskRepresentation):
    """VMDK disk image file representation."""

    disk_format = "vmdk"

    @property
    def disk_subformat(self):
        """Disk subformat, such as 'streamOptimized'."""
        if self._disk_subformat is None:
            # Look at the VMDK file header to determine the sub-format
            with open(self.path, 'rb') as fileobj:
                # The header contains a mix of binary and ASCII, so ignore
                # any errors in decoding binary data to strings
                header = fileobj.read(1000).decode('ascii', 'ignore')
            # Detect the VMDK format from the output:
            match = re.search('createType="(.*)"', header)
            if not match:
                raise RuntimeError(
                    "Could not find VMDK 'createType' in the "
                    "file header:\n{0}".format(header))
            vmdk_format = match.group(1)
            logger.debug("VMDK sub-format for %s is '%s'",
                         self.path, vmdk_format)
            self._disk_subformat = vmdk_format
        return self._disk_subformat

    @classmethod
    def from_other_image(cls, input_image, output_dir,
                         output_subformat="streamOptimized"):
        """Convert the other disk image into an image of this type.

        Args:
          input_image (DiskRepresentation): Existing image representation.
          output_dir (str): Output directory to store the new image in.
          output_subformat (str): VMDK subformat string.
              Defaults to "streamOptimized" if unset.

        Returns:
          VMDK: representation of newly created VMDK file.

        .. note::

          Creation of streamOptimized subformat VMDKs (ESXi's preferred
          subformat for OVAs, hence COT's default subformat) is more complex
          than it seems due to the underlying helpers required.

          - Prior to QEMU 2.1.0, ``qemu-img`` effectively can't write
            streamOptimized subformat at all (it tends to error out).
          - In QEMU 2.1.0 through 2.5.0, ``qemu-img`` supports output to
            streamOptimized subformat, but it outputs VMDK images declaring
            version 1 of the VMDK format, which newer versions of ESXi
            (and probably other VMware products) reject with the message
            ``"Not a supported disk format (sparse VMDK version too old)"``.
          - In QEMU 2.5.1 and later, ``qemu-img`` produces "version 3" VMDK
            images, which suffices to make ESXi happy.
          - ``vmdktool`` (any released version) also makes "version 3" VMDKs,
            but is less likely to be available on most user systems, and it
            can only convert from RAW format images to streamOptimized VMDK.

          So, when creating streamOptimized VMDKs, if we have QEMU 2.5.1+,
          we're golden. Else, if we have ``vmdktool``, use it, after
          converting the :attr:`input_image` to RAW format first if necessary.
          Else, fail back to QEMU 2.1.0+ but warn the user that the resulting
          image may not be usable with ESXi.
        """
        file_name = os.path.basename(input_image.path)
        (file_prefix, _) = os.path.splitext(file_name)
        output_path = os.path.join(output_dir, file_prefix + ".vmdk")
        if output_subformat == "streamOptimized":
            helper = helper_select([
                ('qemu-img', '2.5.1'),  # best option, all needed functionality
                'vmdktool',  # supports VMDK v.3, but only converts from RAW
                ('qemu-img', '2.1.0'),  # fallback - produces VMDK v.1
            ])
            if helper.name == 'vmdktool':
                if input_image.disk_format != 'raw':
                    # vmdktool needs a raw image as input
                    from COT.disks import RAW
                    try:
                        temp_image = RAW.from_other_image(input_image,
                                                          output_dir)
                        return cls.from_other_image(temp_image,
                                                    output_dir,
                                                    output_subformat)
                    finally:
                        os.remove(temp_image.path)

                # Note that vmdktool takes its arguments in unusual order -
                # output file comes before input file
                helper.call(['-z9', '-v', output_path, input_image.path])
                return cls(output_path)

            # else, fall through to default (qemu-img), with one extra:
            if helpers['qemu-img'].version < StrictVersion("2.5.1"):
                logger.warning(
                    "QEMU version %s produces 'version 1' VMDK images, which"
                    " newer versions of VMware ESXi will reject with the"
                    " message '%s'.\nIn order to generate the preferred"
                    " 'version 3' images, please upgrade to QEMU 2.5.1 or"
                    " later, or install vmdktool.",
                    str(helpers['qemu-img'].version),
                    "Not a supported disk format"
                    " (sparse VMDK version too old)")

        helpers['qemu-img'].call([
            'convert',
            '-O', 'vmdk',
            '-o', 'subformat={0}'.format(output_subformat),
            input_image.path,
            output_path])
        return cls(output_path)

    @classmethod
    def _create_file(cls, path, disk_subformat="streamOptimized", **kwargs):
        """Worker function for create_file().

        Args:
          path (str): Location to create VMDK file.
          disk_subformat (str): Defaults to "streamOptimized".
          **kwargs: See :meth:`DiskRepresentation._create_file`
        """
        if (disk_subformat == "streamOptimized" and
                helpers['qemu-img'].version < StrictVersion("2.5.1")):
            # Slightly different warning from the one in from_other_image,
            # as vmdktool doesn't help us with this case.
            logger.warning(
                "QEMU version %s produces 'version 1' VMDK images, which newer"
                " versions of VMware ESXi will reject with the message '%s'."
                "\nIn order to generate the preferred 'version 3' images,"
                " please upgrade to QEMU 2.5.1 or later.",
                str(helpers['qemu-img'].version),
                "Not a supported disk format (sparse VMDK version too old)")

        super(VMDK, cls)._create_file(path, disk_subformat=disk_subformat,
                                      **kwargs)
