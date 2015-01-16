#!/usr/bin/env python
#
# check_and_install_helpers.py - installer helper script for COT package
#
# October 2014, Glenn F. Matthews
# Copyright (c) 2014-2015 the COT project developers.
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
import re
import shutil
import subprocess
import sys

# In python 2.x, we want raw_input, but in python 3 we want input.
try: input = raw_input
except NameError: pass

def confirm(prompt, force=False):
    """Prompts user to confirm the requested operation, or auto-accepts if
       args.force is set to True."""
    if force or not sys.__stdin__.isatty():
        return True

    while True:
        ans = input("{0} [y] ".format(prompt))
        if not ans or ans == 'y' or ans == 'Y':
            return True
        elif ans == 'n' or ans == 'N':
            return False
        else:
            print("Please enter 'y' or 'n'")

def confirm_or_die(prompt, force=False):
    """If the user doesn't agree, abort!"""
    if not confirm(prompt, force):
        sys.exit("Aborting.")

def check_output(args, require_success=True):
    try:
        # In 2.7+ we can use subprocess.check_output(), but in 2.6,
        # we have to work around its absence.
        if "check_output" not in dir( subprocess ):
            process = subprocess.Popen(args,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
            stdout, _ = process.communicate()
            retcode = process.poll()
            if retcode and require_success:
                raise subprocess.CalledProcessError(retcode, " ".join(args))
        else:
            stdout = (subprocess.check_output(args, stderr=subprocess.STDOUT)
                      .decode())
    except subprocess.CalledProcessError as e:
        if require_success:
            raise
        try:
            stdout = e.output.decode()
        except AttributeError:
            # CalledProcessError doesn't have 'output' in 2.6
            stdout = "(output unavailable)"
    return stdout

def get_qemu_img_version():
    qemu_stdout = check_output(['qemu-img', '--version'], require_success=False)
    qemu_match = re.search("qemu-img version ([0-9.]+)", qemu_stdout)
    return StrictVersion(qemu_match.group(1))

# Look for various package managers:
PORT = distutils.spawn.find_executable('port')
APT_GET = distutils.spawn.find_executable('apt-get')
YUM = distutils.spawn.find_executable('yum')

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

    qemu_version = get_qemu_img_version()
    print("QEMU version is {0}".format(qemu_version))

    if qemu_version >= StrictVersion("2.1.0"):
        print("QEMU is new enough that 'vmdktool' is not required")
        return True

    print("Checking for 'vmdktool' executable...")

    return check_executable('vmdktool')


def install_qemu_and_vmdktool(force):
    if check_qemu_and_vmdktool():
        return True

    if not check_executable('qemu-img'):
        confirm_or_die("qemu-img not found. Try to install it?", force)
        if PORT:
            subprocess.check_call(['port', 'install', 'qemu'])
        elif APT_GET:
            subprocess.check_call(['apt-get', 'install', 'qemu'])
        elif YUM:
            subprocess.check_call(['yum', 'install', 'qemu-img'])
        else:
            exit("Not sure how to install QEMU without 'port' or 'apt-get'!\n"
                 "Please install QEMU before proceeding.\n"
                 "See http://en.wikibooks.org/wiki/QEMU/Installing_QEMU")
    qemu_version = get_qemu_img_version()

    print("installed qemu version is {0}".format(qemu_version))

    if qemu_version >= StrictVersion("2.1.0"):
        print("vmdktool is not required")
        return True

    if not distutils.spawn.find_executable('vmdktool'):
        confirm_or_die("vmdktool not found. Try to install it?", force)
        if PORT:
            subprocess.check_call(['port', 'install', 'vmdktool'])
        elif APT_GET or YUM:
            # We don't have vmdktool in apt or yum yet,
            # but we can build it manually:
            # vmdktool requires make and zlib
            if not check_executable('make'):
                if APT_GET:
                    subprocess.check_call(['apt-get', 'install', 'make'])
                else:
                    subprocess.check_call(['yum', 'install', 'make'])
            if APT_GET:
                subprocess.check_call(['apt-get', 'install', 'zlib1g-dev'])
            else:
                subprocess.check_call(['yum', 'install', 'zlib-devel'])
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
                    os.makedirs('/usr/local/man/man8', 493) # 0o755
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


def install_fatdisk(force):
    if check_fatdisk():
        return True

    if not confirm("Optional dependency 'fatdisk' not found. "
                   "Try to install it?", force):
        return False

    if PORT:
        subprocess.check_call(['port', 'install', 'fatdisk'])
    elif sys.platform == 'linux2':
        # Fatdisk installation requires make
        if not check_executable('make'):
            subprocess.check_call(['apt-get', 'install', 'make'])
            if APT_GET:
                subprocess.check_call(['apt-get', 'install', 'make'])
            else:
                exit("Not sure how to install 'make', sorry!")
        subprocess.check_call(['wget', '-O', 'fatdisk.tgz',
            'https://github.com/goblinhack/fatdisk/archive/master.tar.gz'])
        subprocess.check_call(['tar', 'zxf', 'fatdisk.tgz'])
        subprocess.check_call(['./RUNME'], cwd='fatdisk-master')
        shutil.copy2('fatdisk-master/fatdisk', '/usr/local/bin/fatdisk')
    else:
        print("Not sure how to install 'fatdisk', sorry!\n"
              "See https://github.com/goblinhack/fatdisk")
        return False

    return check_fatdisk()


def check_mkisofs():
    return (check_executable('mkisofs') or check_executable('genisoimage'))


def install_mkisofs(force):
    if check_mkisofs():
        return True

    if not confirm("Optional dependency 'mkisofs'/'genisoimage' not found. "
                   "Try to install it?", force):
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


def install_ovftool(force):
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

        if len(sys.argv) > 2 and sys.argv[2] == '-f':
            force = True
        else:
            force = False

        if sys.platform == 'darwin' and not PORT:
            confirm_or_die("It appears you are running on a Mac but "
                           "do not have MacPorts installed.\n"
                           "If you've already installed all helper programs "
                           "that COT needs, this is not a problem.\n"
                           "If any helpers are missing, we could use MacPorts "
                           "to automatically install them for you... "
                           "if it were installed!\n"
                           "See https://www.macports.org/\n"
                           "Continue?", force)
        elif sys.platform == 'linux2' and (not APT_GET and not YUM):
            confirm_or_die("It appears you are running on a Linux that doesn't "
                           "have 'apt-get' or 'yum' capability.\n"
                           "If you've already installed all helper programs "
                           "that COT needs, this is not a problem.\n"
                           "Continue?", force)

        install_qemu_and_vmdktool(force)
        install_fatdisk(force)
        install_mkisofs(force)
        install_ovftool(force)
    else:
        exit("Unknown subcommand '{0}'!".format(sys.argv[1]))

if __name__ == "__main__":
    main()
