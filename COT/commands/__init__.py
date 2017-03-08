# February 2017, Glenn F. Matthews
# Copyright (c) 2017 the COT project developers.
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
Package describing various operations COT can perform on a VM description.

API
---

.. autosummary::
  :nosignatures:

  Command
  ReadCommand
  ReadWriteCommand

Command modules
---------------

.. autosummary::
  :toctree:

  COT.commands.add_disk
  COT.commands.add_file
  .. COT.commands.demo_logging
  COT.commands.deploy
  COT.commands.deploy_esxi
  COT.commands.edit_hardware
  COT.commands.edit_product
  COT.commands.edit_properties
  COT.commands.help
  COT.commands.info
  COT.commands.inject_config
  COT.commands.install_helpers
  COT.commands.remove_file
"""

from .command import command_classes, Command, ReadCommand, ReadWriteCommand

# flake8: noqa: F401
from .add_disk import COTAddDisk
from .add_file import COTAddFile
# from .demo_logging import COTDemoLogging
from .deploy_esxi import COTDeployESXi
from .edit_hardware import COTEditHardware
from .edit_product import COTEditProduct
from .edit_properties import COTEditProperties
from .help import COTHelp
from .info import COTInfo
from .inject_config import COTInjectConfig
from .install_helpers import COTInstallHelpers
from .remove_file import COTRemoveFile

__all__ = (
    'command_classes',
    'Command',
    'ReadCommand',
    'ReadWriteCommand',
)
