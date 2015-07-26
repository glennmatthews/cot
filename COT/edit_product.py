#!/usr/bin/env python
#
# edit_product.py - Implements "edit-product" sub-command
#
# August 2013, Glenn F. Matthews
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

"""Module for editing product information in a VM description.

**Classes**

.. autosummary::
  :nosignatures:

  COTEditProduct
"""

import logging

from .submodule import COTSubmodule

logger = logging.getLogger(__name__)


class COTEditProduct(COTSubmodule):

    """Edit product information (short version, long version, product,
                                 product_url, vendor, vendor_url,
                                 application_url).

    Inherited attributes:
    :attr:`~COTGenericSubmodule.UI`,
    :attr:`~COTSubmodule.package`,
    :attr:`~COTSubmodule.output`

    Attributes:
    :attr:`product`
    :attr:`vendor`
    :attr:`version`,
    :attr:`full_version`
    :attr:`product_url`
    :attr:`vendor_url`
    :attr:`application_url`
    """

    def __init__(self, UI):
        """Instantiate this submodule with the given UI."""
        super(COTEditProduct, self).__init__(UI)
        self.product = None
        """Product string."""
        self.vendor = None
        """Vendor string."""
        self.version = None
        """Short version string."""
        self.full_version = None
        """Long version string."""
        self.product_url = None
        """Product URL string."""
        self.vendor_url = None
        """Application url string."""
        self.application_url = None

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        :returns: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        ready, reason = super(COTEditProduct, self).ready_to_run()
        if not ready:
            return ready, reason

        work_to_do = False
        if self.product is not None:
            work_to_do = True
        elif self.vendor is not None:
            work_to_do = True
        elif self.version is not None:
            work_to_do = True
        elif self.full_version is not None:
            work_to_do = True
        elif self.product_url is not None:
            work_to_do = True
        elif self.vendor_url is not None:
            work_to_do = True
        elif self.application_url is not None:
            work_to_do = True

        if not work_to_do:
            return False, ("""Neither product, vendor, version, full version,
            product url, vendor url, nor application url was specified"""
                           "- nothing to do!")
        return ready, reason

    def run(self):
        """Do the actual work of this submodule.

        :raises InvalidInputError: if :func:`ready_to_run` reports ``False``
        """
        super(COTEditProduct, self).run()
        if self.product is not None:
            self.vm.product = self.product
        if self.vendor is not None:
            self.vm.vendor = self.vendor
        if self.version is not None:
            self.vm.version_short = self.version
        if self.full_version is not None:
            self.vm.version_long = self.full_version
        if self.product_url is not None:
            self.vm.product_url = self.product_url
        if self.vendor_url is not None:
            self.vm.vendor_url = self.vendor_url
        if self.application_url is not None:
            self.vm.application_url = self.application_url

    def create_subparser(self, parent, storage):
        """Add subparser for the CLI of this submodule.

        :param object parent: Subparser grouping object returned by
            :meth:`ArgumentParser.add_subparsers`

        :param dict storage: Dict of { 'label': subparser } to be updated with
            subparser(s) created, if any.
        """
        p = parent.add_parser(
            'edit-product',
            help="""Edit product info in an OVF""",
            usage=self.UI.fill_usage(
                "edit-product",
                ["""PACKAGE [-o OUTPUT] [-p PRODUCT] [-n VENDOR] [-v SHORT_VERSION]
                    [-V FULL_VERSION] [-u PRODUCT_URL ] [-r VENDOR_URL]
                    [-l APPLICATION_URL]""",
                 ]),
            description="""Edit product information attributes of the given OVF or OVA""")

        p.add_argument(
            '-o',
            '--output',
            help="""Name/path of new OVF/OVA package to create """
            """instead of updating the existing OVF""")
        p.add_argument('-p', '--product',
                       help="""Product name string, such as """
                       """"Cisco IOS-XE" """)
        p.add_argument('-n', '--vendor',
                       help="""Vendor string, such as """
                       """"Cisco Systems, Inc."  """)
        p.add_argument(
            '-v',
            '--version',
            metavar="SHORT_VERSION",
            help="""Software short version string, such as """
            """"15.3(4)S" or "5.2.0.01I" """)
        p.add_argument('-V', '--full-version',
                       help="""Software long version string, such as """
                       """"Cisco IOS-XE Software, Version 15.3(4)S" """)
        p.add_argument(
            '-u',
            '--product-url',
            help="""Product url string, such as """
            """"http://www.cisco.com/c/en/us/products/ios-nx-os-software/ios-xe/index.html" """)
        p.add_argument('-r', '--vendor-url',
                       help="""Vendor URL string, such as """
                       """"http://www.cisco.com"  """)
        p.add_argument('-l', '--application-url',
                       help="""Application URL string, such as """
                       """"https://router1:530/"  """)
        p.add_argument('PACKAGE',
                       help="""OVF descriptor or OVA file to edit""")
        p.set_defaults(instance=self)

        storage['edit-product'] = p
