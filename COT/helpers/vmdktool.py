#!/usr/bin/env python
#
# vmdktool.py - Helper for 'vmdktool'
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2013-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Give COT access to ``vmdktool`` for manipulating compressed VMDK files.

http://www.freshports.org/sysutils/vmdktool/
"""

import logging
import os
import os.path
import platform

from .helper import Helper

logger = logging.getLogger(__name__)


class VmdkTool(Helper):
    """Helper provider for ``vmdktool``.

    http://www.freshports.org/sysutils/vmdktool/

    **Methods**

    .. autosummary::
      :nosignatures:

      install_helper
      convert_disk_image
    """

    def __init__(self):
        """Initializer."""
        super(VmdkTool, self).__init__(
            "vmdktool",
            version_args=['-V'],
            version_regexp="vmdktool version ([0-9.]+)")

    def install_helper(self):
        """Install ``vmdktool``."""
        if self.path:
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.name, self.path))
            return
        logger.info("Installing 'vmdktool'...")
        if Helper.port_install('vmdktool'):
            pass
        elif platform.system() == 'Linux':
            # We don't have vmdktool in apt or yum yet,
            # but we can build it manually:
            # vmdktool requires make and zlib
            if not self.find_executable('make'):
                logger.info("vmdktool requires 'make'... installing 'make'")
                if not (Helper.apt_install('make') or
                        Helper.yum_install('make')):
                    raise NotImplementedError("Not sure how to install 'make'")
            logger.info("vmdktool requires 'zlib'... installing 'zlib'")
            if not (Helper.apt_install('zlib1g-dev') or
                    Helper.yum_install('zlib-devel')):
                raise NotImplementedError("Not sure how to install 'zlib'")
            with self.download_and_expand('http://people.freebsd.org/~brian/'
                                          'vmdktool/vmdktool-1.4.tar.gz') as d:
                new_d = os.path.join(d, "vmdktool-1.4")
                logger.info("Compiling 'vmdktool'")
                # vmdktool is originally a BSD tool so it has some build
                # assumptions that aren't necessarily correct under Linux.
                # The easiest workaround is to override the CFLAGS to:
                # 1) add -D_GNU_SOURCE
                # 2) not treat all warnings as errors
                self._check_call(['make',
                                  'CFLAGS="-D_GNU_SOURCE -g -O -pipe"'],
                                 cwd=new_d)
                destdir = os.getenv('DESTDIR', '')
                prefix = os.getenv('PREFIX', '/usr/local')
                args = ['make', 'install', 'PREFIX=' + prefix]
                if destdir != '':
                    args.append('DESTDIR=' + destdir)
                    # os.path.join doesn't like absolute paths in the middle
                    prefix = prefix.lstrip(os.sep)
                logger.info("Compilation complete, installing to " +
                            os.path.join(destdir, prefix))
                # Make sure the relevant man and bin directories exist
                self.make_install_dir(os.path.join(destdir, prefix,
                                                   'man', 'man8'))
                self.make_install_dir(os.path.join(destdir, prefix, 'bin'))
                try:
                    self._check_call(args, cwd=new_d)
                except OSError:
                    logger.verbose("Installation failed, trying sudo")
                    self._check_call(['sudo'] + args, cwd=new_d)
        else:
            raise NotImplementedError(
                "Unsure how to install vmdktool.\n"
                "See http://www.freshports.org/sysutils/vmdktool/")
        logger.info("Successfully installed 'vmdktool'")

    def convert_disk_image(self, file_path, output_dir,
                           new_format, new_subformat=None):
        """Convert the given disk image to the requested format/subformat.

        If the disk is already in this format then it is unchanged;
        otherwise, will convert to a new disk in the specified output_dir
        and return its path.

        Current supported conversions:

        * .vmdk (any format) to .vmdk (streamOptimized)
        * .img to .vmdk (streamOptimized)

        :param str file_path: Disk image file to inspect/convert
        :param str output_dir: Directory to place converted image into, if
          needed
        :param str new_format: Desired final format
        :param str new_subformat: Desired final subformat
        :return:
          * :attr:`file_path`, if no conversion was required
          * or a file path in :attr:`output_dir` containing the converted image

        :raise NotImplementedError: if the :attr:`new_format` and/or
          :attr:`new_subformat` are not supported conversion targets.
        """
        file_name = os.path.basename(file_path)
        (file_string, file_extension) = os.path.splitext(file_name)

        new_file_path = None

        if new_format == 'vmdk' and new_subformat == 'streamOptimized':
            new_file_path = os.path.join(output_dir, file_string + '.vmdk')
            logger.info("Invoking vmdktool to convert {0} to "
                        "stream-optimized VMDK {1}"
                        .format(file_path, new_file_path))
            # Note that vmdktool takes its arguments in unusual order -
            # output file comes before input file
            self.call_helper(['-z9', '-v', new_file_path, file_path])
        else:
            raise NotImplementedError("No support for converting disk image "
                                      "to format {0} / subformat {1}"
                                      .format(new_format, new_subformat))

        return new_file_path
