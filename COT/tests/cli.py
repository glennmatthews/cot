#!/usr/bin/env python
#
# cli.py - Unit test cases for generic COT CLI.
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

import os.path

from COT.tests.ut import COT_UT
from COT.cli import mac_address, device_address
from argparse import ArgumentTypeError

class TestCLIGeneral(COT_UT):
    """CLI Test cases for top-level "cot" command"""

    def test_help(self):
        """Verifying help menu"""
        self.call_cot(['-h'])
        self.call_cot(['--help'])


    def test_version(self):
        """Verifying --version command"""
        self.call_cot(['-V'])
        self.call_cot(['--version'])


    def test_incomplete_cli(self):
        """Verifying command with no subcommand is not valid"""
        # No args at all
        self.call_cot([], result=2)
        # Optional args but no subcommand
        self.call_cot(['-f', '-vvv'], result=2)


class TestCLIAddDisk(COT_UT):
    """CLI test cases for "cot add-disk" command"""

    def test_help(self):
        """Verifying help menu"""
        self.call_cot(['add-disk', "-h"])


    def test_invalid_args(self):
        """Testing various missing or incorrect parameters"""
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        # No disk or VM specified
        self.call_cot(['add-disk'], result=2)
        # Disk but no VM
        self.call_cot(['add-disk', disk_path], result=2)
        # Nonexistent VM specified
        self.call_cot(['add-disk', disk_path, '/foo'], result=2)
        # Incorrect type parameter
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-t', 'dvd'],
                      result=2)
        # Incorrect controller parameter
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ata'],
                      result=2)
        # Incorrectly formatted address parameter
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ide',
                       '-a', "1"], result=2)
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ide',
                       '-a', ":1"], result=2)
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ide',
                       '-a', "1600 Pennsylvania Avenue"], result=2)
        # Correctly formatted but out-of-range address parameters:
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ide',
                       '-a', "2:0"], result=2)
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ide',
                       '-a', "0:2"], result=2)
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'scsi',
                       '-a', "4:0"], result=2)
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'scsi',
                       '-a', "0:16"], result=2)

        # Missing strings
        for param in ['-f', '-t', '-c', '-a', '-s', '-d', '-n']:
            self.call_cot(['add-disk', disk_path, self.input_ovf, param],
                          result=2)
        # Package file exists but filename shows it is not an OVF/OVA
        self.call_cot(['add-disk', disk_path, disk_path], result=2)
        # Package file claims to be an OVF/OVA, but is not actually XML.
        fake_file = os.path.join(self.temp_dir, "foo.ovf")
        with open(fake_file, 'w') as f:
            f.write("< hello world!")
        self.call_cot(['add-disk', disk_path, fake_file], result=2)
        # Package file claims to be an OVF/OVA, but is some other XML.
        with open(fake_file, 'w') as f:
            f.write("<xml />")
        self.call_cot(['add-disk', disk_path, fake_file], result=2)

    def test_nonexistent_file(self):
        """Pass in a file or VM that doesn't exist"""
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        # Disk exists but VM does not
        self.call_cot(['add-disk', disk_path, '/foo/bar.ovf'], result=2)
        # VM exists but disk does not
        self.call_cot(['add-disk', '/foo/bar.vmdk', self.input_ovf],
                      result=2)

    def test_unknown_filetype(self):
        """Pass in a file that is not obviously a CDROM or hard disk"""
        # Unknown extension
        mystery_file = os.path.join(self.temp_dir, "foo.bar")
        open(mystery_file, 'a').close()
        self.call_cot(['add-disk', mystery_file, self.input_ovf],
                      result=2)
        # No extension
        mystery_file = os.path.join(self.temp_dir, "foo")
        open(mystery_file, 'a').close()
        self.call_cot(['add-disk', mystery_file, self.input_ovf],
                      result=2)


class TestCLIAddFile(COT_UT):
    """CLI test cases for "cot add-file" command"""

    def test_help(self):
        """Verifying help menu"""
        self.call_cot(['add-file', "-h"])


    def test_invalid_args(self):
        """Testing various missing or incorrect parameters"""
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        # No file or VM specified
        self.call_cot(['add-file'], result=2)
        # File but no VM
        self.call_cot(['add-file', disk_path], result=2)
        # Nonexistent VM specified
        self.call_cot(['add-file', disk_path, '/foo'], result=2)
        # Missing strings
        for param in ['-f']:
            self.call_cot(['add-file', disk_path, self.input_ovf, param],
                          result=2)

    def test_nonexistent_file(self):
        """Pass in a file or VM that doesn't exist"""
        disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        # Disk exists but VM does not
        self.call_cot(['add-file', disk_path, '/foo/bar.ovf'], result=2)
        # VM exists but disk does not
        self.call_cot(['add-file', '/foo/bar.vmdk', self.input_ovf],
                      result=2)


class TestCLIEditHardware(COT_UT):
    """CLI test cases for "cot edit-hardware" command"""

    def test_help(self):
        """Verifying help menu"""
        self.call_cot(['edit-hardware', "-h"])


    def test_invalid_args(self):
        """Testing various missing or incorrect parameters"""
        # No VM specified
        self.call_cot(['edit-hardware'], result=2)
        # Nonexistent VM specified
        self.call_cot(['edit-hardware', '/foo', '-o', self.temp_file],
                      result=2)

        base_args = ['edit-hardware', self.input_ovf,
                     '-o', self.temp_file]
        # Arguments missing values
        for arg in ['-p', '--profile', '-c', '--cpus',
                    '-m', '--memory', '-n', '--nics',
                    '-N', '--nic-networks',
                    '--nic-type', '--nic-count',
                    '-M', '--mac-addresses-list',
                    '-s', '--serial-ports', '-S', '--serial-connectivity',
                    '--scsi-subtype', '--ide-subtype',
                    '-v', '--virtual-system-type']:
            self.call_cot(base_args + [arg], result=2)
        # Invalid profile string
        self.call_cot(base_args + ['-p', '2 CPUs, 2 GB RAM'], result=2)
        # Invalid CPUs value
        for arg in ['-c', '--cpus']:
            self.call_cot(base_args + [arg, '0'], result=2)
        # Invalid memory value
        self.call_cot(base_args + ['-m', '512k'], result=2)
        self.call_cot(base_args + ['--memory', '0'], result=2)
        # Invalid MAC address
        self.call_cot(base_args + ['-M', 'fe:fi:f0:ff:ff:ff'], result=2)
        # Invalid NIC type
        self.call_cot(base_args + ['--nic_type', 'GLENN'], result=2)


class TestCLIEditProduct(COT_UT):
    """CLI test cases for "cot edit-product" command"""

    def test_help(self):
        """Verifying help menu"""
        self.call_cot(['edit-product', "-h"])


    def test_invalid_args(self):
        """Testing various missing or incorrect parameters"""
        # No VM specified
        self.call_cot(['edit-product'], result=2)
        # Nonexistent VM specified
        self.call_cot(['edit-product', '/foo'], result=2)
        # Missing strings
        self.call_cot(['edit-product', self.input_ovf, '-v'], result=2)
        self.call_cot(['edit-product', self.input_ovf, '-V'], result=2)
        self.call_cot(['edit-product', self.input_ovf, '-V', '-v'], result=2)


class TestCLIEditProperties(COT_UT):
    """CLI test cases for "cot edit-properties" command"""

    def test_help(self):
        """Verifying help menu"""
        self.call_cot(['edit-properties', '-h'])


    def test_invalid_args(self):
        """Testing various missing or incorrect parameters"""
        # No VM specified
        self.call_cot(['edit-properties'], result=2)
        # Nonexistent VM specified
        self.call_cot(['edit-properties', '/foo'], result=2)
        # Missing strings
        self.call_cot(['edit-properties', self.input_ovf, '--config-file'],
                      result=2)
        self.call_cot(['edit-properties', self.input_ovf, '--properties'],
                      result=2)
        self.call_cot(['edit-properties', self.input_ovf, '--output'],
                      result=2)
        # Nonexistent files
        self.call_cot(['edit-properties', self.input_ovf, '--config-file',
                       '/foo'], result=2)
        # Bad input format
        self.call_cot(['edit-properties', self.input_ovf, '--properties', 'x'],
                      result=2)
        self.call_cot(['edit-properties', self.input_ovf, '--properties', '='],
                      result=2)
        self.call_cot(['edit-properties', self.input_ovf, '--properties',
                       '=foo'], result=2)


class TestCLIInfo(COT_UT):
    """CLI test cases for "cot info" command"""

    def test_help(self):
        """Verifying help menu"""
        self.call_cot(['info', "-h"])


class TestCLIInjectConfig(COT_UT):
    """CLI test cases for "cot inject-config" command"""

    def test_help(self):
        """Verifying help menu"""
        self.call_cot(['inject-config', '-h'])

    def test_invalid_args(self):
        """Testing various missing or incorrect parameters"""
        # No VM specified
        self.call_cot(['inject-config'], result=2)
        # Nonexistent VM specified
        self.call_cot(['inject-config', '/foo'], result=2)
        # Missing strings
        self.call_cot(['inject-config', self.input_ovf, '-c'], result=2)
        self.call_cot(['inject-config', self.input_ovf, '-s'], result=2)
        # Nonexistent config files
        self.call_cot(['inject-config', self.input_ovf,
                       '-c', '/foo'], result=2)
        self.call_cot(['inject-config', self.input_ovf,
                       '-s', '/foo'], result=2)

class TestCLIDeploy(COT_UT):
    """CLI test cases for "cot deploy" command"""

    def test_help(self):
        """Verifying help menu"""
        self.call_cot(['deploy', '-h'])

    def test_invalid_args(self):
        # No VM specified
        self.call_cot(['deploy'], result = 2)
        # VM does not exist
        self.call_cot(['deploy', '/foo'], result=2)
        # Hypervisor not specified
        self.call_cot(['deploy', self.input_ovf], result=2)
        # Invalid hypervisor
        self.call_cot(['deploy', self.input_ovf, 'MyHypervisor'], result=2)


class TestCLIDeployESXi(COT_UT):
    """CLI test cases for 'cot deploy PACKAGE esxi' command"""

    def test_help(self):
        "Verifying help menu"
        self.call_cot(['deploy', self.input_ovf, '-h'])

    def test_invalid_args(self):
        # No locator specified
        self.call_cot(['deploy', self.input_ovf, 'esxi'],
                      result=2)
        # No password specified - required if running noninteractively
        self.call_cot(['deploy', self.input_ovf, 'esxi', 'localhost'],
                      result=2)
        # Missing strings
        for param in ['-c', '-n', '-N', '-u', '-p', '-d', '-o']:
            self.call_cot(['deploy', self.input_ovf, 'esxi', 'localhost',
                           '-p', 'password', param],
                          result=2)
        # Invalid configuration profile
        self.call_cot(['deploy', self.input_ovf, 'esxi', 'localhost',
                       '-p', 'password', '-c', 'nonexistent'],
                      result=2)
