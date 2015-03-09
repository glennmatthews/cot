#!/bin/sh
#
# zipme.sh - simple script to create a tgz distribution of the COT package.
#
# May 2014, Glenn F. Matthews
# Copyright (c) 2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

set -e

COT="$1"

if [ "$COT" == "" ]; then
    echo "ERROR: must specify root directory of COT package"
    exit 1
fi

set -u

VERSION=`grep __version__ $COT/COT/__version__.py | cut -f 2 -d'"'`

ARCHIVE="cot-$VERSION.tgz"

tar czvf $ARCHIVE \
    $COT/*.md \
    $COT/*.rst \
    $COT/*.txt \
    $COT/*.in \
    $COT/*.py \
    $COT/bin/cot \
    $COT/bin/*.sh \
    $COT/docs/*.rst \
    $COT/docs/*.py \
    $COT/docs/Makefile \
    $COT/COT/*.py \
    $COT/COT/tests/*.py \
    $COT/COT/tests/*.ovf \
    $COT/COT/tests/*.mf \
    $COT/COT/tests/*.vmdk \
    $COT/COT/tests/*.iso \
    $COT/COT/tests/*.txt \
    $COT/COT/helpers/*.py \
    $COT/COT/helpers/tests/*.py

echo "Successfully created $ARCHIVE"
exit 0
