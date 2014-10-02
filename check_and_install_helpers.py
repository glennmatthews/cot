#!/usr/bin/env python
#
# check_and_install_helpers.py - installer helper script for COT package
#
# October 2014, Glenn F. Matthews
#
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

import distutils.spawn

import COT.helper_tools
from COT.helper_tools import HelperNotFoundError, HelperError
from COT.cli import confirm_or_die
from distutils.version import StrictVersion

def check_qemu_and_vmdktool():
    print("Checking for qemu-img executable...")
    try:
        qemu_version = COT.helper_tools.get_qemu_img_version()
    except HelperNotFoundError:
        COT.cli.confirm_or_die("qemu-img not found. Try to install it?")
        # TODO
        qemu_version = COT.helper_tools.get_qemu_img_version()

    print("installed qemu version is {0}".format(qemu_version))

    if qemu_version >= StrictVersion("2.1.0"):
        print("vmdktool is not required")
        return

    print("Checking for vmdktool executable...")

    if not distutils.spawn.find_executable('vmdktool'):
        confirm_or_die("vmdktool not found. Try to install it?")
        # TODO

    print("vmdktool is available")
    return


def check_fatdisk():
    if not distutils.spawn.find_executable('fatdisk'):
        confirm_or_die("fatdisk not found. Try to install it?")
        # TODO

    print("fatdisk is available")
    return

def check_mkisofs():
    if not distutils.spawn.find_executable('mkisofs'):
        confirm_or_die("mkisofs not found. Try to install it?")
        # TODO

    print("mkisofs is available")
    return

def check_ovftool():
    if not distutils.spawn.find_executable('ovftool'):
        confirm_or_die("ovftool not found. Try to install it?")
        # TODO

    print("ovftool is available")
    return

def main():
    check_qemu_and_vmdktool()
    check_fatdisk()
    check_mkisofs()
    check_ovftool()

if __name__ == "__main__":
    main()
