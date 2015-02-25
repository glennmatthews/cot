#!/usr/bin/env python
#
# install_helpers.py - Implements "cot install-helpers" command
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2014-2015 the COT project developers.
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

import logging
import textwrap

from .submodule import COTGenericSubmodule

logger = logging.getLogger(__name__)


class COTInstallHelpers(COTGenericSubmodule):

    """Install all helper tools that COT requires."""

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTInstallHelpers, self).__init__(UI)
        self.verify_only = False

    def run(self):
        """Verify all helper tools and install any that are missing."""
        from COT.helpers import FatDisk, MkIsoFS, OVFTool, QEMUImg, VmdkTool
        from COT.helpers import HelperError, HelperNotFoundError
        result = True
        results = {}
        for cls in [FatDisk, MkIsoFS, OVFTool, QEMUImg, VmdkTool]:
            helper = cls()
            if helper.find_helper():
                results[helper.helper] = "already installed"
            elif self.verify_only:
                results[helper.helper] = "NOT installed"
            else:
                try:
                    helper.install_helper()
                    results[helper.helper] = "installation SUCCEEDED"
                except (NotImplementedError,
                        HelperError,
                        HelperNotFoundError) as e:
                    results[helper.helper] = "installation FAILED: " + str(e)
                    result = False

        print("Results:")
        print("-------------")
        wrapper = textwrap.TextWrapper(width=self.UI.terminal_width(),
                                       initial_indent="",
                                       subsequent_indent=(" " * 14))
        for k in sorted(results.keys()):
            print(wrapper.fill("{0:13} {1}".format(k + ":", results[k])))
        if not result:
            raise EnvironmentError(1, "Unable to install some helpers")

    def create_subparser(self, parent):
        """Add subparser for the CLI of this submodule.

        :param object parent: Subparser grouping object returned by
            :func:`ArgumentParser.add_subparsers`

        :returns: ``('install-helpers', subparser)``
        """
        p = parent.add_parser(
            'install-helpers',
            help="Install third-party helper programs that COT may require",
            usage=self.UI.fill_usage('install-helpers',
                                     ["[--verify-only]"]),
            description="Install third-party helper programs for COT")

        # TODO - nice to have!
        # p.add_argument('--dry-run', action='store_true',
        #              help="Report the commands that would be run to install "
        #             "any helper programs, but do not actually run them.")

        p.add_argument('--verify-only', action='store_true',
                       help="Only verify helpers, do not attempt to install "
                       "any missing helpers.")

        p.set_defaults(instance=self)

        return 'install-helpers', p
