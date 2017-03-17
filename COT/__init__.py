# September 2013, Glenn F. Matthews
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

"""
Package implementing the Common OVF Tool.

Utility modules
---------------
.. autosummary::
  :toctree:

  COT.data_validation
  COT.file_reference
  COT.utilities
  COT.xml_file

Sub-packages
------------
.. autosummary::
  :toctree:

  COT.commands
  COT.disks
  COT.helpers
  COT.platforms
  COT.ui
  COT.vm_description

.. note::
  The hierarchy of permissible imports between sub-packages is as follows::

      COT.ui
         |
         +---> COT.commands
         |        |
         |        +---> COT.vm_description
         |        |        |
         |        |        +---> COT.platforms
         |        |        |
         |        +--------+---> COT.disks
         |        |                 |
         +--------+-----------------+---> COT.helpers

  Thus, to avoid circular dependencies, none of the other sub-packages may
  ``import COT.ui`` - if they wish to interact with the UI in any way
  (e.g., :mod:`COT.helpers` prompting the user to confirm whether to try
  to install a helper program), this needs to be done with a callback object
  (e.g., :attr:`COT.helpers.Helper.USER_INTERFACE`) rather than an import of
  the other module.
"""

import logging

# VerboseLogger adds a log level 'verbose' between 'info' and 'debug'.
# This lets us be a bit more fine-grained in our logging verbosity.
from verboselogs import VerboseLogger

from ._version import get_versions

logging.setLoggerClass(VerboseLogger)
logging.captureWarnings(True)

__version__ = get_versions()['version']
del get_versions

__version_long__ = (
    """Common OVF Tool (COT), version """ + __version__ +
    """\nCopyright (C) 2013-2017 the COT project developers."""
)
