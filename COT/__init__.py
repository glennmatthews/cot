# September 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution.

import os.path

version_file = os.path.join(os.path.dirname(__file__), '__version__.py')
# Work under python 2.x and 3.x both
try:
    # python 2
    execfile(version_file)
except NameError:
    # python 3
    exec(compile(open(version_file, "rb").read(), version_file, 'exec'))
