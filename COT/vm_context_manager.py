#!/usr/bin/env python
#
# vm_context_manager.py - Context manager for virtual machine definitions
#
# September 2013, Glenn F. Matthews
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

import logging

from .vm_factory import VMFactory

logger = logging.getLogger(__name__)

class VMContextManager:
    """Context manager for virtual machine definitions. Use as follows:
    with VM_Context_manager(input_file, output_file) as vm:
        vm.foo()
        vm.bar()
    """

    def __init__(self, input_file, output_file):
        self.obj = VMFactory.create(input_file, output_file)


    def __enter__(self):
        return self.obj


    def __exit__(self, type, value, trace):
        # Did we exit cleanly?
        if type is None:
            self.obj.write()
        self.obj.destroy()
