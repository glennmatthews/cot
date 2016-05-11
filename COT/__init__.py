# September 2013, Glenn F. Matthews
# Copyright (c) 2013-2016 the COT project developers.
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

Virtual machine definition modules
----------------------------------
.. autosummary::
  :toctree:

  COT.vm_description
  COT.vm_factory
  COT.vm_context_manager
  COT.xml_file
  COT.ovf

Command modules
---------------
.. autosummary::
  :toctree:

  COT.submodule
  COT.add_disk
  COT.add_file
  COT.deploy
  COT.deploy_esxi
  COT.edit_hardware
  COT.edit_product
  COT.edit_properties
  COT.help
  COT.info
  COT.inject_config
  COT.install_helpers

Helper library modules
----------------------
.. autosummary::
  :toctree:

  COT.data_validation
  COT.file_reference
  COT.platforms

User interface modules
----------------------
.. autosummary::
  :toctree:

  COT.ui_shared
  COT.cli
"""

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

__version_long__ = (
    """Common OVF Tool (COT), version """ + __version__ +
    """\nCopyright (C) 2013-2016 the COT project developers."""
)
