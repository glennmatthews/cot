# February 2015, Glenn F. Matthews
# Copyright (c) 2015-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""
Provides a common interface for interacting with various non-Python programs.

API
---

.. autosummary::
  :nosignatures:

  Helper
  helpers
  helper_select

Exceptions
----------

.. autosummary::

  ~COT.helpers.helper.HelperError
  ~COT.helpers.helper.HelperNotFoundError

Helper modules
--------------

.. autosummary::
  :toctree:

  COT.helpers.helper
  COT.helpers.apt_get
  COT.helpers.brew
  COT.helpers.fatdisk
  COT.helpers.gcc
  COT.helpers.isoinfo
  COT.helpers.make
  COT.helpers.mkisofs
  COT.helpers.ovftool
  COT.helpers.port
  COT.helpers.qemu_img
  COT.helpers.vmdktool
  COT.helpers.yum
"""

from .helper import (
    Helper, PackageManager, helpers,
    HelperError, HelperNotFoundError, helper_select,
)

# flake8: noqa: F401

from .apt_get import AptGet
from .brew import Brew
from .fatdisk import FatDisk
from .gcc import GCC
from .isoinfo import ISOInfo
from .make import Make
from .mkisofs import MkISOFS, GenISOImage, XorrISO
from .ovftool import OVFTool
from .port import Port
from .qemu_img import QEMUImg
from .vmdktool import VMDKTool
from .yum import Yum

# pylint doesn't know about __subclasses__
# https://github.com/PyCQA/pylint/issues/555
# TODO: this should be fixed when pylint 2.0 is released
# pylint:disable=no-member


# Populate helpers dictionary
for cls in Helper.__subclasses__():
    if cls is PackageManager:
        # Don't record the abstract class!
        continue
    ins = cls()
    helpers[ins.name] = ins


for cls in PackageManager.__subclasses__():
    ins = cls()
    helpers[ins.name] = ins


__all__ = (
    'Helper',
    'HelperError',
    'HelperNotFoundError',
    'helpers',
    'helper_select',
)
