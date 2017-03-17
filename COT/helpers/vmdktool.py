#!/usr/bin/env python
#
# vmdktool.py - Helper for 'vmdktool'
#
# February 2015, Glenn F. Matthews
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

"""Give COT access to ``vmdktool`` for manipulating compressed VMDK files.

http://www.freshports.org/sysutils/vmdktool/
"""

import logging
import os
import os.path
import platform

from COT.helpers.helper import Helper, helpers, check_call

logger = logging.getLogger(__name__)


class VMDKTool(Helper):
    """Helper provider for ``vmdktool``.

    http://www.freshports.org/sysutils/vmdktool/
    """

    _provider_package = {
        'brew': 'vmdktool',
        'port': 'vmdktool',
    }

    def __init__(self):
        """Initializer."""
        super(VMDKTool, self).__init__(
            "vmdktool",
            info_uri="http://www.freshports.org/sysutils/vmdktool/",
            version_args=['-V'],
            version_regexp="vmdktool version ([0-9.]+)")

    @property
    def installable(self):
        """Whether COT is capable of installing this program on this system."""
        return bool(helpers['apt-get'] or
                    helpers['brew'] or
                    helpers['port'] or
                    helpers['yum'])

    def _install(self):
        """Install ``vmdktool``."""
        try:
            super(VMDKTool, self)._install()
            return
        except NotImplementedError:
            # We have an alternative install method available for Linux,
            # below - but if not Linux, you're out of luck!
            if platform.system() != 'Linux':
                raise

        # We don't have vmdktool in apt or yum yet,
        # but we can build it manually:
        # vmdktool requires make and zlib
        helpers['make'].install()
        # TODO: check for installed zlib?
        logger.notice("vmdktool requires 'zlib'... installing 'zlib'")
        if helpers['apt-get']:
            helpers['apt-get'].install_package('zlib1g-dev')
        elif helpers['yum']:
            helpers['yum'].install_package('zlib-devel')
        else:
            raise NotImplementedError("Not sure how to install 'zlib'")
        with self.download_and_expand_tgz(
            'http://people.freebsd.org/~brian/vmdktool/vmdktool-1.4.tar.gz'
        ) as directory:
            new_d = os.path.join(directory, "vmdktool-1.4")
            logger.info("Compiling 'vmdktool'")
            # vmdktool is originally a BSD tool so it has some build
            # assumptions that aren't necessarily correct under Linux.
            # The easiest workaround is to override the CFLAGS to:
            # 1) add -D_GNU_SOURCE
            # 2) not treat all warnings as errors
            check_call(['make',
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
            self.mkdir(os.path.join(destdir, prefix, 'man', 'man8'))
            self.mkdir(os.path.join(destdir, prefix, 'bin'))
            check_call(args, retry_with_sudo=True, cwd=new_d)
