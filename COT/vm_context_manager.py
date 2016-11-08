#!/usr/bin/env python
#
# vm_context_manager.py - Context manager for virtual machine definitions
#
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

"""Context manager for virtual machine definitions."""

import logging

from COT.vm_factory import VMFactory

logger = logging.getLogger(__name__)


class VMContextManager(object):
    """Context manager for virtual machine definitions.

    When the context manager exits, unless an error occurred, the virtual
    machine's :meth:`write` method is called. Regardless of whether an error
    occurred, the virtual machine's :meth:`destroy` method is then called.

    Use as follows:
    ::

      with VMContextManager(input_file, output_file) as vm:
          vm.foo()
          vm.bar()

    For the parameters, see :class:`~COT.vm_description.VMDescription`.
    """

    def __init__(self, input_file, output_file=None):
        """Create a VM instance.

        For the parameters, see :class:`~COT.vm_description.VMDescription`.
        """
        self.obj = VMFactory.create(input_file, output_file)

    def __enter__(self):
        """Use the VM instance as the context manager object."""
        return self.obj

    def __exit__(self, exc_type, exc_value, trace):
        """If the block exited cleanly, write the VM out to disk.

        In any case, destroy the VM.
        For the parameters, see :mod:`contextlib`.
        """
        # Did we exit cleanly?
        try:
            if exc_type is None:
                self.obj.write()
        finally:
            self.obj.destroy()
