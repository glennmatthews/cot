#!/usr/bin/env python
#
# logging.py - Common OVF Tool infrastructure for logging
#
# February 2017, Glenn F. Matthews
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

"""Logging module for the Common OVF Tool (COT).

**Classes**

.. autosummary::
  :nosignatures:

  COTFormatter
"""

from __future__ import absolute_import

import logging
from verboselogs import VerboseLogger
from colorlog import ColoredFormatter

# VerboseLogger adds a log level 'verbose' between 'info' and 'debug'.
# This lets us be a bit more fine-grained in our logging verbosity.
logging.setLoggerClass(VerboseLogger)

logger = logging.getLogger(__name__)


class COTFormatter(ColoredFormatter, object):
    r"""Logging formatter with colorization and variable verbosity.

    COT logs are formatted differently (more or less verbosely) depending
    on the logging level.

    .. seealso:: :class:`logging.Formatter`

    Args:
      verbosity (int): Logging level as defined by :mod:`logging`.

    Examples::

      >>> record = logging.LogRecord("test_func", logging.INFO,
      ...                            "/fake.py", 22, "Hello world!",
      ...                            None, None)
      >>> record.created = 0
      >>> record.msecs = 0
      >>> COTFormatter(logging.DEBUG).format(record)   # doctest: +ELLIPSIS
      '\x1b[32m...:00.0     INFO: test_func              Hello world!\x1b[0m'
      >>> COTFormatter(logging.VERBOSE).format(record)
      '\x1b[32m    INFO: test_func              Hello world!\x1b[0m'
      >>> COTFormatter(logging.INFO).format(record)
      '\x1b[32m    INFO: Hello world!\x1b[0m'
    """

    LOG_COLORS = {
        'DEBUG':    'blue',
        'VERBOSE':  'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red',
    }

    def __init__(self, verbosity=logging.INFO):
        """Create formatter for COT log output with the given verbosity."""
        format_string = "%(log_color)s"
        datefmt = None
        if verbosity <= logging.DEBUG:
            format_string += "%(asctime)s.%(msecs)d "
            datefmt = "%H:%M:%S"
        format_string += "%(levelname)8s: "
        if verbosity <= logging.VERBOSE:
            format_string += "%(name)-22s "
        format_string += "%(message)s"
        super(COTFormatter, self).__init__(format_string,
                                           datefmt=datefmt,
                                           log_colors=self.LOG_COLORS)


if __name__ == "__main__":   # pragma: no cover
    import doctest
    doctest.testmod()
