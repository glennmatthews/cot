# September 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

import os.path

version_file = os.path.join(os.path.dirname(__file__), '__version__.py')
# Work under python 2.x and 3.x both
try:
    # python 2
    execfile(version_file)
except NameError:
    # python 3
    exec(compile(open(version_file, "rb").read(), version_file, 'exec'))
