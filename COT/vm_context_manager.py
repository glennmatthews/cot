#!/usr/bin/env python
#
# vm_context_manager.py - Context manager for virtual machine definitions
#
# September 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

import logging
import os.path
import re
import shutil
import sys
import tempfile
import traceback

from .ovf import OVF
from .vm_description import VMInitError
from .data_validation import ValueUnsupportedError

logger = logging.getLogger("cot")

class VMContextManager:
    """Context manager for virtual machine definitions. Use as follows:
    with VM_Context_manager(input_file, output_file) as vm:
        vm.foo()
        vm.bar()
    """

    def __init__(self, input_file, output_file):
        vm_class = None

        supported_types = []
        # Add other VMDescription subclasses as needed
        for candidate_class in [OVF]:
            try:
                filetype = candidate_class.detect_type_from_name(input_file)
                vm_class = candidate_class
                break
            except ValueUnsupportedError as e:
                supported_types += [e.expected_value]

        if not vm_class:
            raise VMInitError(2,
                              "Unknown VM description type for input file "
                              "'{0}' - only supported types are {1}"
                              .format(input_file, supported_types))

        if output_file:
            # Make sure the output format is supported by this class
            try:
                vm_class.detect_type_from_name(output_file)
            except ValueUnsupportedError as e:
                raise VMInitError(2,
                                  "Unsupported format for output file '{0}' - "
                                  "only support {1} for output from {2}"
                                  .format(output_file, e.expected_value,
                                          vm_class.__name__))

        tempdir = tempfile.mkdtemp(prefix="cot")
        try:
            self.obj = vm_class(input_file, tempdir, output_file)
        except Exception as e:
            shutil.rmtree(tempdir)
            raise


    def __enter__(self):
        return self.obj


    def __exit__(self, type, value, trace):
        # Did we exit cleanly?
        if type is None:
            self.obj.write()

        # Clean up after ourselves
        if os.path.exists(self.obj.working_dir):
            shutil.rmtree(self.obj.working_dir)
