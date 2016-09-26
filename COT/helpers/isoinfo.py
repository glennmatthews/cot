#!/usr/bin/env python
#
# isoinfo.py - Helper for 'isoinfo'
#
# September 2016, Glenn F. Matthews
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

"""Give COT access to isoinfo for inspecting ISO images.

http://cdrecord.org/
https://www.gnu.org/software/xorriso/
"""

import logging
import re

from .helper import Helper, HelperError

logger = logging.getLogger(__name__)


class IsoInfo(Helper):
    """Helper provider for ``isoinfo``.

    http://cdrecord.org/

    **Methods**

    .. autosummary::
      :nosignatures:

      get_disk_format
      get_disk_file_listing
    """

    def __init__(self):
        """Initializer."""
        super(IsoInfo, self).__init__("isoinfo",
                                      version_regexp=r"isoinfo ([0-9.]+)")

    # No install support as this is provided by MkIsoFS class.

    def get_disk_format(self, file_path):
        """Get the major disk image format of the given file.

        :param str file_path: Path to disk image file to inspect.
        :return: ``(format, subformat)``, such as:

          * ``(None, None)`` - file is not an ISO
          * ``("iso", None)`` - ISO without Rock Ridge or Joliet extensions
          * ``("iso", "Rock Ridge")`` - ISO with Rock Ridge extensions
        """
        try:
            output = self.call_helper(['-i', file_path, '-d'])
        except HelperError:
            # Not an ISO
            return (None, None)

        # If no exception, isoinfo recognized it as an ISO file.
        subformat = None
        if re.search(r"Rock Ridge.*found", output):
            subformat = "Rock Ridge"
        # At this time we don't care about Joliet extensions
        return ('iso', subformat)

    def get_disk_file_listing(self, file_path):
        """Get the list of files on the given ISO.

        :param str file_path: Path to ISO file to inspect.
        :return: List of file paths, or None on failure
        """
        (iso, subformat) = self.get_disk_format(file_path)
        if iso != "iso":
            return None
        args = ["-i", file_path, "-f"]
        if subformat == "Rock Ridge":
            args.append("-R")
        # At this time we don't support Joliet extensions
        output = self.call_helper(args)
        result = []
        for line in output.split("\n"):
            # discard non-file output lines
            if not line or line[0] != "/":
                continue
            # Non-Rock-Ridge filenames look like this in isoinfo:
            # /IOSXR_CONFIG.TXT;1
            # but the actual filename thus is:
            # /iosxr_config.txt
            if subformat != "Rock Ridge" and ";1" in line:
                line = line.lower()[:-2]
            # Strip the leading '/'
            result.append(line[1:])
        return result
