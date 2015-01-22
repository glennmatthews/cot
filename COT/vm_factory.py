#!/usr/bin/env python
#
# vm_factory.py - Factory for virtual machine objects
#
# December 2014, Glenn F. Matthews
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

from .ovf import OVF
from .vm_description import VMInitError
from .data_validation import ValueUnsupportedError

logger = logging.getLogger(__name__)


class VMFactory:
    """Class for creating a VMDescription instance (of indeterminate subclass)
    from a specified input file."""

    @classmethod
    def create(cls, input_file, output_file):
        vm_class = None

        supported_types = []
        # Add other VMDescription subclasses as needed
        for candidate_class in [OVF]:
            try:
                candidate_class.detect_type_from_name(input_file)
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

        logger.info("Loading '{0}' as {1}".format(input_file,
                                                  vm_class.__name__))
        vm = vm_class(input_file, output_file)
        logger.debug("Loaded VM object from {0}".format(input_file))

        return vm
