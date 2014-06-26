#!/usr/bin/env python
#
# helper_tools.py - Module to abstract away operations that require third-party
#                   helper software not part of a standard Python distro.
#
# April 2014, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

import logging
import os
import re
import subprocess

from .data_validation import ValueUnsupportedError

logger = logging.getLogger('cot')

class HelperNotFoundError(OSError):
    """Error thrown when a helper program cannot be located."""

class HelperError(EnvironmentError):
    """Error thrown when a helper program exits with non-zero return code."""

def check_output(args):
    """Wrapper for subprocess.check_output.
    1) Raises a HelperNotFoundError if the command doesn't exist, instead of
       an OSError.
    2) Raises a HelperError if the command doesn't return 0 when run,
       instead of subprocess.CalledProcessError.
    3) Automatically redirects stderr to stdout, captures both, and generates
       a debug message with the stdout contents.
    """
    cmd = args[0]
    logger.debug("Calling {0}".format(" ".join(args)))
    try:
        stdout = (subprocess.check_output(args, stderr=subprocess.STDOUT)
                  .decode())
    except OSError as e:
        raise HelperNotFoundError(e.errno,
                                  "Unable to locate helper program '{0}'. "
                                  "Please check your $PATH.".format(cmd))
    except subprocess.CalledProcessError as e:
        raise HelperError(e.returncode,
                          "Helper program '{0}' exited with error {1}:\n"
                          "> {2}\n{3}".format(cmd, e.returncode,
                                              " ".join(args),
                                              e.output.decode()))
    logger.debug("{0} output:\n{1}".format(cmd, stdout))
    return stdout


def get_checksum(file_path, checksum_type):
    """Get the checksum of the given file.
    Supported checksum_type values are 'md5' and 'sha1'.
    """

    if checksum_type == 'md5':
        try:
            md5sum = check_output(['md5sum', file_path])
            # md5sum outputs something like:
            # 835a7493384047fde776d6e0f6ccb492  foo.ovf
            # We only want the first part of this string
            return md5sum.split(" ")[0]
        except HelperNotFoundError:
            md5sum = check_output(['md5', file_path])
            # md5 outputs something like:
            # MD5 (foo.ovf) = 835a7493384047fde776d6e0f6ccb492
            # We want the last part of this string, minus any trailing \n
            return md5sum.strip().split(" ")[-1]
    elif checksum_type == 'sha1':
        # Depending on the platform we can use either 'sha1sum' or 'shasum'
        try:
            sha1sum = check_output(['sha1sum', file_path])
        except HelperNotFoundError:
            sha1sum = check_output(['shasum', '-a', '1', file_path])
        # sha1sum and shasum both output something like:
        # 1309dfbf9a556def784fa3cc011a2b1f343024ba foo.ovf
        # We only want the first part of this string
        return sha1sum.split(" ")[0]
    else:
        raise ValueUnsupportedError("checksum type",
                                    checksum_type,
                                    "'md5' or 'sha1'")


def get_disk_format(file_path):
    """Returns a tuple (format, subformat) representing the given disk file's
    file format.

    format may be 'vmdk', 'raw', or 'qcow2'
    subformat may be None, or one of many strings for 'vmdk' files.
    """

    logger.info("Invoking qemu-img to determine disk format of {0}"
                .format(file_path))
    qemu_stdout = check_output(['qemu-img', 'info', file_path])
    # Read the format from the output
    match = re.search("file format: (.*)", qemu_stdout)
    if not match:
        raise RuntimeError("Did not find file format string in "
                           "the output from qemu-img:\n{0}"
                           .format(qemu_stdout))
    file_format = match.group(1)
    logger.info("File format is {0}".format(file_format))

    if file_format == 'raw':
        # No applicable sub-format
        return (file_format, None)
    elif file_format == 'qcow2':
        # No applicable sub-format
        return (file_format, None)
    elif file_format == 'vmdk':
        # Look at the VMDK file header to determine the sub-format
        with open(file_path, 'rb') as f:
            # The header contains a fun mix of binary and ASCII, so ignore
            # any errors in decoding binary data to strings
            header = f.read(1000).decode(errors='ignore')
            # Detect the VMDK format from the output:
            match = re.search('createType="(.*)"', header)
            if not match:
                raise RuntimeError("Could not find VMDK 'createType' in the "
                                   "file header:\n{0}".format(header))
            vmdk_format = match.group(1)
        logger.info("VMDK sub-format is {0}".format(vmdk_format))
        return (file_format, vmdk_format)
    else:
        raise ValueUnsupportedError("disk file format",
                                    file_format,
                                    "'raw' or 'qcow2' or 'vmdk'")


def get_disk_capacity(file_path):
    """Get the storage capacity of the given disk image.
    """
    qemu_stdout = check_output(['qemu-img', 'info', file_path])
    match = re.search(r"(\d+) bytes", qemu_stdout)
    if not match:
        raise RuntimeError("Did not find byte count in the output from "
                           "qemu-img:\n{0}"
                           .format(qemu_stdout))
    capacity = match.group(1)
    logger.info("Disk {0} capacity is {1} bytes".format(file_path, capacity))
    return capacity


def convert_disk_image(file_path, output_dir, new_format, new_subformat=None):
    """Convert the given disk image to the requested format
    (and optional subformat).
    If the disk is already in this format then return the same file_path;
    otherwise, create a new disk in the specified output_dir
    and return its path.

    Current supported conversions:
    .vmdk (any format) to .vmdk (streamOptimized)
    .img to .vmdk (streamOptimized)
    """

    curr_format, curr_subformat = get_disk_format(file_path)

    if curr_format == new_format and curr_subformat == new_subformat:
        logger.info("Disk image {0} is already in '{1}' format - "
                    "no conversion required."
                    .format(file_path,
                            (new_format if not new_subformat else
                             (new_format + "," + new_subformat))))
        return file_path

    file_name = os.path.basename(file_path)
    (file_string, file_extension) = os.path.splitext(file_name)

    new_file_path = None
    temp_path = None # any temporary file we should delete before returning

    if new_format == 'vmdk' and new_subformat == 'streamOptimized':
        # We have to pass through raw format on the way, even if the existing
        # image is a non-streamOptimized vmdk.
        if curr_format != 'raw':
            # Use qemu-img to convert to raw format
            temp_path = os.path.join(output_dir, file_string + '.img')
            logger.warning("Invoking qemu-img to convert {0} to RAW {1}"
                           .format(file_path, temp_path))
            qemu_stdout = check_output(['qemu-img', 'convert', '-O', 'raw',
                                        file_path, temp_path])
            file_path = temp_path

        # Use vmdktool to convert raw image to stream-optimized VMDK
        new_file_path = os.path.join(output_dir, file_string + '.vmdk')
        logger.warning("Invoking vmdktool to convert {0} to "
                       "stream-optimized VMDK {1}"
                       .format(file_path, new_file_path))
        # Note that vmdktool takes its arguments in unusual order -
        # output file comes before input file
        vmdktool_so = check_output(['vmdktool', '-z9', '-v',
                                    new_file_path, file_path])
    else:
        raise ValueUnsupportedError("new file format/subformat",
                                    (new_format, new_subformat),
                                    "(vmdk,streamOptimized)")

    logger.info("Successfully converted from ({0},{1}) to ({2},{3})"
                .format(curr_format, curr_subformat, new_format, new_subformat))

    if temp_path is not None:
        os.remove(temp_path)

    return new_file_path


def create_disk_image(file_path, file_format=None,
                      capacity=None, contents=[]):
    """Create a new disk image at the requested location.
    Either 'capacity' (for a blank disk) or 'contents' (a list of files,
    for a non-empty disk) or both must be specified.
    """

    if not capacity and not contents:
        raise RuntimeError("Either capacity or contents must be specified!")

    if not file_format:
        # Guess format from file extension
        file_format = os.path.splitext(file_path)[1][1:]
        if file_format == 'img':
            file_format = 'raw'
        logger.debug("guessed file format is {0}".format(file_format))

    if not contents:
        qemu_stdout = check_output(['qemu-img', 'create', '-f',
                                    file_format, file_path, capacity])
        return True

    if file_format == 'iso':
        mkisofs_args = ['mkisofs',
                        '-output', file_path,
                        '-full-iso9660-filenames',
                        '-iso-level', '2'] + contents
        check_output(mkisofs_args)
    elif file_format == 'raw' or file_format == 'img':
        # Create a blank disk and format it to FAT32
        if not capacity:
            # What size disk do we need to contain the requested file(s)?
            capacity = 0
            for content_file in contents:
                capacity += os.path.getsize(content_file)
            # Round capacity to the next larger multiple of 8 MB
            # just to be safe...
            capacity = "{0}M".format(((capacity/1024/1024/8) + 1)*8)
            logger.debug("To contain files {0}, disk capacity will be {1}"
                         .format(contents, capacity))
        # TODO - if fatdisk not available, use qemu-img and guestfish?
        fatdisk_args = ['fatdisk', file_path, 'format',
                        'size', capacity,
                        'fat32', # TODO make user-configurable?
                        ]
        check_output(fatdisk_args)
        # Upload files to the root of the disk
        for content_file in contents:
            fatdisk_args = ['fatdisk', file_path, 'fileadd',
                            content_file, os.path.basename(content_file)]
            check_output(fatdisk_args)
    else:
        raise ValueUnsupportedError("new disk file format",
                                    file_format,
                                    "'iso' or 'raw' or 'img'")

    return True

def validate_ovf_for_esxi(ovf_file):
    """Use VMware's 'ovftool' program to validate an OVF or OVA against the
    OVF standard and any VMware-specific requirements.
    """

    check_output(['ovftool', '--schemaValidate', ovf_file])
