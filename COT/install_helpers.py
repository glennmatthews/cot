#!/usr/bin/env python
#
# install_helpers.py - Implements "cot install-helpers" command
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2014-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Implements "install-helpers" command."""

import argparse
import filecmp
import logging
import os
import shutil
import sys
import textwrap
from pkg_resources import resource_listdir, resource_filename

from .submodule import COTGenericSubmodule
from COT.helpers import HelperError, HelperNotFoundError

logger = logging.getLogger(__name__)


class COTInstallHelpers(COTGenericSubmodule):
    """Install all helper tools that COT requires."""

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTInstallHelpers, self).__init__(UI)
        self.ignore_errors = False
        self.verify_only = False

    def install_helper(self, helper):
        """Install the given helper module.

        :return: (result, message)
        """
        if helper.path:
            return (True,
                    "version {0}, present at {1}"
                    .format(helper.version, str(helper.path)))
        elif self.verify_only:
            return (True, "NOT FOUND")
        else:
            try:
                helper.install_helper()
                return (True,
                        "successfully installed to {0}, version {1}"
                        .format(str(helper.path), helper.version))
            except (NotImplementedError,
                    HelperError,
                    HelperNotFoundError) as e:
                return (False, "INSTALLATION FAILED: " + str(e))

    def install_manpages(self):
        """Install COT's manual pages.

        :return: (result, message)
        """
        installed_any = False
        some_preinstalled = False
        try:
            resource_listdir("COT", "docs/man")
        except OSError as e:
            return False, "UNABLE TO FIND PAGES: " + str(e)

        # If COT is installed in /foo/bar/bin/cot, man pages go in /foo/bar/man
        bin_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        logger.debug("invoked from directory: {0}".format(sys.argv[0]))
        if os.path.basename(bin_dir) == 'bin':
            man_dir = os.path.join(os.path.dirname(bin_dir), "man")
            logger.verbose("program install directory {0} matches 'bin', "
                           "so assume relative man path {1}"
                           .format(bin_dir, man_dir))
        else:
            man_dir = "/usr/local/man"
            logger.verbose("program install directory {0} does not appear "
                           "to be 'bin', assuming system install path {0}"
                           .format(man_dir))

        for f in resource_listdir("COT", "docs/man"):
            src_path = resource_filename("COT", os.path.join("docs/man", f))
            # Which man section does this belong in?
            section = os.path.splitext(f)[1][1:]
            dest = os.path.join(man_dir, "man{0}".format(section))
            if not os.path.exists(dest):
                if self.verify_only:
                    return True, "DIRECTORY NOT FOUND: {0}".format(dest)
                logger.verbose("Creating manpage directory {0}".format(dest))
                try:
                    os.makedirs(dest)
                except OSError as e:
                    return False, "INSTALLATION FAILED: " + str(e)

            dest_path = os.path.join(dest, f)
            if os.path.exists(dest_path):
                some_preinstalled = True
                if filecmp.cmp(src_path, dest_path):
                    logger.verbose("File {0} does not need to be updated"
                                   .format(dest_path))
                    continue
                if self.verify_only:
                    return True, "NEEDS UPDATE"
            elif self.verify_only:
                return True, "NOT FOUND"
            logger.info("Copying {0} to {1}".format(f, dest_path))
            try:
                shutil.copy(src_path, dest_path)
            except IOError as e:
                return False, "INSTALLATION FAILED: " + str(e)
            installed_any = True

        if some_preinstalled:
            if not installed_any:
                return True, "already installed, no updates needed"
            return True, "successfully updated in {0}".format(man_dir)
        return True, "successfully installed to {0}".format(man_dir)

    def run(self):
        """Verify all helper tools and install any that are missing."""
        from COT.helpers.fatdisk import FatDisk
        from COT.helpers.mkisofs import MkIsoFS
        from COT.helpers.ovftool import OVFTool
        from COT.helpers.qemu_img import QEMUImg
        from COT.helpers.vmdktool import VmdkTool
        result = True
        results = {}
        for cls in [FatDisk, MkIsoFS, OVFTool, QEMUImg, VmdkTool]:
            helper = cls()
            rc, results[helper.name] = self.install_helper(helper)
            if not rc:
                result = False

        rc, results["COT manpages"] = self.install_manpages()
        if not rc:
            result = False

        print("Results:")
        print("-------------")
        wrapper = textwrap.TextWrapper(width=self.UI.terminal_width,
                                       initial_indent="",
                                       subsequent_indent=(" " * 14))
        for k in sorted(results.keys()):
            print(wrapper.fill("{0:13} {1}".format(k + ":", results[k])))
        print("")
        if not result and not self.ignore_errors:
            raise EnvironmentError(1, "Unable to install some helpers")

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        :param object parent: Subparser grouping object returned by
            :meth:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
        p = parent.add_parser(
            'install-helpers',
            help=("Install/verify COT manual pages and any third-party helper "
                  "programs that COT may require"),
            usage=self.UI.fill_usage('install-helpers',
                                     ["--verify-only",
                                      "[--ignore-errors]"]),
            description="""
Install or verify the installation of COT manual pages and various required
third-party helper programs for COT.

* qemu-img (http://www.qemu.org/)
* mkisofs  (http://cdrecord.org/)
* ovftool  (https://www.vmware.com/support/developer/ovf/)
* fatdisk  (http://github.com/goblinhack/fatdisk)
* vmdktool (http://www.freshports.org/sysutils/vmdktool/)""",
            epilog=self.UI.fill_examples([
                ("Verify whether COT can find all expected helper programs",
                 """
> cot install-helpers --verify-only
Results:
-------------
COT manpages: present in /usr/share/man/man1/
fatdisk:      present at /opt/local/bin/fatdisk
mkisofs:      present at /opt/local/bin/mkisofs
ovftool:      present at /usr/local/bin/ovftool
qemu-img:     present at /opt/local/bin/qemu-img
vmdktool:     NOT FOUND""".strip()),
                ("Have COT attempt to install missing helpers for you. "
                 "Note that most helpers require administrator / ``sudo`` "
                 "privileges to install. If any installation fails, "
                 "COT will exit with an error, unless you pass "
                 "``--ignore-errors``.",
                 """
> cot install-helpers
    INFO: Installing 'fatdisk'...
    INFO: Compiling 'fatdisk'
    INFO: Calling './RUNME'...
(...)
    INFO: ...done
    INFO: Compilation complete, installing to /usr/local/bin
    INFO: Successfully installed 'fatdisk'
    INFO: Calling 'fatdisk --version' and capturing its output...
    INFO: ...done
    INFO: Installing 'vmdktool'...
    INFO: vmdktool requires 'zlib'... installing 'zlib'
    INFO: Calling 'dpkg -s zlib1g-dev' and capturing its output...
    INFO: ...done
    INFO: Compiling 'vmdktool'
    INFO: Calling 'make CFLAGS="-D_GNU_SOURCE -g -O -pipe"'...
(...)
    INFO: ...done
    INFO: Compilation complete, installing to /usr/local
    INFO: Calling 'make install'...
install -s vmdktool /usr/local/bin/
install vmdktool.8 /usr/local/man/man8/
    INFO: ...done
    INFO: Successfully installed 'vmdktool'
    INFO: Calling 'vmdktool -V' and capturing its output...
    INFO: ...done
    INFO: Copying cot-add-disk.1 to /usr/share/man/man1/cot-add-disk.1
(...)
    INFO: Copying cot.1 to /usr/share/man/man1/cot.1
Results:
-------------
COT manpages: successfully installed to /usr/share/man
fatdisk:      successfully installed to /usr/local/bin/fatdisk
mkisofs:      present at /usr/bin/mkisofs
ovftool:      INSTALLATION FAILED: No support for automated
              installation of ovftool, as VMware requires a site
              login to download it. See
              https://www.vmware.com/support/developer/ovf/
qemu-img:     present at /usr/bin/qemu-img
vmdktool:     successfully installed to /usr/local/bin/vmdktool

Unable to install some helpers""".strip())]),
            formatter_class=argparse.RawDescriptionHelpFormatter)

        group = p.add_mutually_exclusive_group()

        # TODO - nice to have!
        # p.add_argument('--dry-run', action='store_true',
        #              help="Report the commands that would be run to install "
        #             "any helper programs, but do not actually run them.")

        group.add_argument('--verify-only', action='store_true',
                           help="Only verify helpers -- do not attempt to "
                           "install any missing helpers.")

        group.add_argument('-i', '--ignore-errors', action='store_true',
                           help="Do not fail even if helper installation "
                           "fails.")

        p.set_defaults(instance=self)

        storage['install-helpers'] = p
