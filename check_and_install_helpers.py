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
from distutils.version import StrictVersion
import os
import os.path
import shutil
import subprocess
import sys

import COT.helper_tools
from COT.helper_tools import HelperNotFoundError
from COT.cli import confirm, confirm_or_die

# Look for various package managers:
PORT = distutils.spawn.find_executable('port')
APT_GET = distutils.spawn.find_executable('apt-get')

def check_executable(name):
    print("Checking for '{0}' executable...".format(name))
    path = distutils.spawn.find_executable(name)
    if path:
        print("Found '{0}'".format(path))
        return True
    else:
        print("'{0}' not found".format(name))
        return False


def check_qemu_and_vmdktool():
    if not check_executable('qemu-img'):
        return False

    qemu_version = COT.helper_tools.get_qemu_img_version()
    print("QEMU version is {0}".format(qemu_version))

    if qemu_version >= StrictVersion("2.1.0"):
        print("QEMU is new enough that 'vmdktool' is not required")
        return True

    print("Checking for 'vmdktool' executable...")

    return check_executable('vmdktool')


def install_qemu_and_vmdktool():
    if check_qemu_and_vmdktool():
        return True

    try:
        qemu_version = COT.helper_tools.get_qemu_img_version()
    except HelperNotFoundError:
        COT.cli.confirm_or_die("qemu-img not found. Try to install it?")
        if PORT:
            subprocess.check_call(['port', 'install', 'qemu'])
        elif APT_GET:
            subprocess.check_call(['apt-get', 'install', 'qemu'])
        else:
            exit("Not sure how to install QEMU without 'port' or 'apt-get'!\n"
                 "Please install QEMU before proceeding.\n"
                 "See http://en.wikibooks.org/wiki/QEMU/Installing_QEMU")
        qemu_version = COT.helper_tools.get_qemu_img_version()

    print("installed qemu version is {0}".format(qemu_version))

    if qemu_version >= StrictVersion("2.1.0"):
        print("vmdktool is not required")
        return True

    if not distutils.spawn.find_executable('vmdktool'):
        confirm_or_die("vmdktool not found. Try to install it?")
        if PORT:
            subprocess.check_call(['port', 'install', 'vmdktool'])
        elif APT_GET:
            # We don't have vmdktool in apt yet but we can build it manually:
            # vmdktool requires make and zlib1g-dev
            if not check_executable('make'):
                subprocess.check_call(['apt-get', 'install', 'make'])
            subprocess.check_call(['apt-get', 'install', 'zlib1g-dev'])
            try:
                # Get the source
                subprocess.check_call(['wget',
                                       'http://people.freebsd.org/~brian/'
                                       'vmdktool/vmdktool-1.4.tar.gz'])
                subprocess.check_call(['tar', 'zxf', 'vmdktool-1.4.tar.gz'])
                # vmdktool is originally a BSD tool so it has some build
                # assumptions that aren't necessarily correct under Linux.
                # The easiest workaround is to override the CFLAGS to:
                # 1) add -D_GNU_SOURCE
                # 2) not treat all warnings as errors
                subprocess.check_call(['make',
                                       'CFLAGS=-D_GNU_SOURCE -g -O -pipe',
                                       '--directory', 'vmdktool-1.4'])
                if not os.path.exists('/usr/local/man/man8'):
                    os.makedirs('/usr/local/man/man8', 0755)
                subprocess.check_call(['make', '--directory', 'vmdktool-1.4',
                                       'install'])
            finally:
                if os.path.exists('vmdktool-1.4.tar.gz'):
                    os.remove('vmdktool-1.4.tar.gz')
                if os.path.exists('vmdktool-1.4'):
                    shutil.rmtree('vmdktool-1.4')
        else:
            exit("Not sure how to install 'vmdktool', sorry!\n"
                 "See http://www.freshports.org/sysutils/vmdktool/")

    print("installed 'vmdktool' successfully")
    return True


def check_fatdisk():
    return check_executable('fatdisk')


def install_fatdisk():
    if check_fatdisk():
        return True

    if not confirm("Optional dependency 'fatdisk' not found. "
                   "Try to install it?"):
        return False

    if PORT:
        subprocess.check_call(['port', 'install', 'fatdisk'])
    elif sys.platform == 'linux2':
        # Fatdisk installation requires unzip and make
        if not check_executable('unzip'):
            if APT_GET:
                subprocess.check_call(['apt-get', 'install', 'unzip'])
            else:
                exit("Not sure how to install 'unzip', sorry!")
        if not check_executable('make'):
            subprocess.check_call(['apt-get', 'install', 'make'])
            if APT_GET:
                subprocess.check_call(['apt-get', 'install', 'make'])
            else:
                exit("Not sure how to install 'make', sorry!")
        subprocess.check_call(['wget', '-O', 'fatdisk.zip',
            'https://github.com/goblinhack/fatdisk/archive/master.zip'])
        subprocess.check_call(['unzip', 'fatdisk.zip'])
        subprocess.check_call(['./RUNME'], cwd='fatdisk-master')
        shutil.copy2('fatdisk-master/fatdisk', '/usr/local/bin/fatdisk')
    else:
        print("Not sure how to install 'fatdisk', sorry!\n"
              "See https://github.com/goblinhack/fatdisk")
        return False

    return check_fatdisk()


def check_mkisofs():
    return (check_executable('mkisofs') or check_executable('genisoimage'))


def install_mkisofs():
    if check_mkisofs():
        return True

    if not confirm("Optional dependency 'mkisofs'/'genisoimage' not found. "
                   "Try to install it?"):
        return False

    if PORT:
        subprocess.check_call(['port', 'install', 'cdrtools'])
    elif APT_GET:
        subprocess.check_call(['apt-get', 'install', 'genisoimage'])
    else:
        print("Not sure how to install mkisofs, sorry!\n"
              "See http://cdrecord.org/")
        return False

    return check_mkisofs()


def check_ovftool():
    return check_executable('ovftool')


def install_ovftool():
    if check_ovftool():
        return True

    print("ovftool (optional dependency) not installed.\n"
          "See https://www.vmware.com/support/developer/ovf/")
    return False


def main():
    if len(sys.argv) < 2:
        exit("Usage: {0} [check, install]".format(sys.argv[0]))
    if sys.argv[1] == "check":
        print("Checking for required and optional helper programs...")
        check_qemu_and_vmdktool()
        check_fatdisk()
        check_mkisofs()
        check_ovftool()
    elif sys.argv[1] == "install":
        print("Installing required and optional helper programs...")

        if sys.platform == 'darwin' and not PORT:
            confirm_or_die("It appears you are running on a Mac but "
                           "do not have MacPorts installed.\n"
                           "If you've already installed all helper programs "
                           "that COT needs, this is not a problem.\n"
                           "If any helpers are missing, we could use MacPorts "
                           "to automatically install them for you... "
                           "if it were installed!\n"
                           "See https://www.macports.org/\n"
                           "Continue?")
        elif sys.platform == 'linux2' and not APT_GET:
            confirm_or_die("It appears you are running on a Linux that doesn't "
                           "have 'apt-get' capability.\n"
                           "If you've already installed all helper programs "
                           "that COT needs, this is not a problem.\n"
                           "Continue?")

        install_qemu_and_vmdktool()
        install_fatdisk()
        install_mkisofs()
        install_ovftool()
    else:
        exit("Unknown subcommand '{0}'!".format(sys.argv[1]))

if __name__ == "__main__":
    main()
