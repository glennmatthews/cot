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
from .apt_get import AptGet       # noqa
from .brew import Brew            # noqa
from .fatdisk import FatDisk      # noqa
from .gcc import GCC              # noqa
from .isoinfo import ISOInfo      # noqa
from .make import Make            # noqa
from .mkisofs import MkISOFS, GenISOImage, XorrISO   # noqa
from .ovftool import OVFTool      # noqa
from .port import Port            # noqa
from .qemu_img import QEMUImg     # noqa
from .vmdktool import VMDKTool    # noqa
from .yum import Yum              # noqa

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
    'HelperError',
    'HelperNotFoundError',
    'helpers',
    'helper_select',
)
