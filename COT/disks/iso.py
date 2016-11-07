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

"""Handling of ISO files."""

import os
import re

from COT.disks.disk import DiskRepresentation
from COT.helpers import helpers, HelperError, helper_select


class ISO(DiskRepresentation):
    """ISO 9660 disk image file representation."""

    disk_format = "iso"

    @property
    def disk_subformat(self):
        """ISO sub-format.

        Possible values:

        - "" - not Rock Ridge
        - "rockridge" - has Rock Ridge extensions
        """
        if self._disk_subformat is None:
            output = helpers['isoinfo'].call(['-i', self.path, '-d'])
            if re.search(r"Rock Ridge.*found", output):
                self._disk_subformat = "rockridge"
            else:
                # At this time we don't care about Joliet extensions
                self._disk_subformat = ""
        return self._disk_subformat

    @property
    def files(self):
        """The list of files contained in this ISO."""
        if self._files is None:
            if helpers['isoinfo']:    # TODO
                # It's safe to specify -R even for non-rockridge ISOs
                args = ["-i", self.path, "-f", "-R"]
                # At this time we don't support Joliet extensions
                output = helpers['isoinfo'].call(args)
                result = []
                for line in output.split("\n"):
                    # discard non-file output lines
                    if not line or line[0] != "/":
                        continue
                    # Non-Rock-Ridge filenames look like this in isoinfo:
                    # /IOSXR_CONFIG.TXT;1
                    # but the actual filename thus is:
                    # /iosxr_config.txt
                    if self.disk_subformat != "rockridge" and ";1" in line:
                        line = line.lower()[:-2]
                    # Strip the leading '/'
                    result.append(line[1:])
                self._files = result
        return self._files

    def _create_file(self):
        """Create an ISO file."""
        if not self._files:
            raise RuntimeError("Unable to create an empty ISO file")
        # Default subformat is to include Rock Ridge extensions.
        # To not have these, use subformat=""
        if self._disk_subformat is None:
            self._disk_subformat = 'rockridge'
        # We can use mkisofs, genisoimage, or xorriso, and fortunately
        # all three take similar parameters
        args = ['-output', self.path, '-full-iso9660-filenames',
                '-iso-level', '2', '-allow-lowercase']
        if self._disk_subformat == 'rockridge':
            args.append('-r')
        args += self.files
        helper = helper_select(['mkisofs', 'genisoimage', 'xorriso'])
        if helper.name == "xorriso":
            args = ['-as', 'mkisofs'] + args
        helper.call(args)

        self._disk_subformat = None
        self._files = None

    @classmethod
    def file_is_this_type(cls, path):
        """Detect whether the given file is an ISO image."""
        if not os.path.exists(path):
            raise HelperError(2, "No such file or directory: '{0}'"
                              .format(path))
        if helpers['isoinfo']:
            try:
                helpers['isoinfo'].call(['-i', path, '-d'])
                return True
            except HelperError:
                # Not an ISO
                return False

        # else, try to detect ISO files by file magic number
        with open(path, 'rb') as f:
            for offset in (0x8001, 0x8801, 0x9001):
                f.seek(offset)
                magic = f.read(5).decode('ascii', 'ignore')
                if magic == "CD001":
                    return True
        return False

    @classmethod
    def from_other_image(cls, input_image, output_dir, output_subformat=None):
        """Convert the other disk image into an image of this type.

        :param DiskRepresentation input_image: Existing image representation.
        :param str output_dir: Output directory to store the new image in.
        :param str output_subformat: Any relevant subformat information.
        :rtype: instance of DiskRepresentation or subclass
        """
        raise NotImplementedError("Not a valid target for conversion")